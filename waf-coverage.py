import argparse
import boto3
import csv
import os
from tqdm import tqdm

# ToDo: avaliar API Gateway

parser = argparse.ArgumentParser(description='Set AWS SSO profiles from a CSV file.')
parser.add_argument('--input-file', default='workspace/aws_profiles.csv', help='Input CSV file. Default is aws_profiles.csv.')
parser.add_argument('--output-file', default='workspace/waf_coverage.csv', help='Output CSV file. Default is waf_coverage.csv.')

args = parser.parse_args()

input_csv_filepath = os.path.expanduser(args.input_file)
output_file_path, output_file_extension = os.path.splitext(args.output_file)
elb_csv_filepath = os.path.expanduser(f'{output_file_path}_for_elb{output_file_extension}')
cloudfront_csv_filepath = os.path.expanduser(f'{output_file_path}_for_cloudfront{output_file_extension}')


def read_profiles_from_csv(csv_filepath):
    profiles = []
    with open(csv_filepath, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            profiles.append({
                'sso_session': row['sso_session'],
                'profile_name': row['profile_name'],
                'account_id': row['account_id']
            })
    return profiles


def get_all_elbv2_load_balancers(elbv2_client, page_size=400):
    elbs_v2 = []
    paginator = elbv2_client.get_paginator('describe_load_balancers')
    for page in paginator.paginate(PaginationConfig={'PageSize': page_size}):
        elbs_v2.extend(page['LoadBalancers'])
    return elbs_v2


def get_all_elbv1_load_balancers(elb_client, page_size=400):
    elbs_v1 = []
    paginator = elb_client.get_paginator('describe_load_balancers')
    for page in paginator.paginate(PaginationConfig={'PageSize': page_size}):
        elbs_v1.extend(page['LoadBalancerDescriptions'])
    return elbs_v1


def get_all_cloudfront_distributions(cloudfront_client):
    distributions = []
    paginator = cloudfront_client.get_paginator('list_distributions')
    for page in paginator.paginate():
        for distribution in page['DistributionList'].get('Items', []):
            distributions.append(distribution)
    return distributions


def get_elbv2_info(elbv2_client, wafv2_client, profile_info):
    elbs_v2 = get_all_elbv2_load_balancers(elbv2_client)

    elb_info_list = []
    for elb in tqdm(elbs_v2):
        tags_response = elbv2_client.describe_tags(ResourceArns=[elb['LoadBalancerArn']])
        tags = tags_response['TagDescriptions'][0]['Tags']
        waf_ignore = any(tag['Key'] == 'et:waf-ignore' for tag in tags)

        elb_info = {
            'sso_session': profile_info['sso_session'],
            'profile_name': profile_info['profile_name'],
            'account_id': profile_info['account_id'],
            'name': elb['LoadBalancerName'],
            'version': 'v2',
            'type': elb['Type'],
            'scheme': elb['Scheme'],
            'associated_waf': 'None',
            'marked_as_waf_ignore': waf_ignore
        }

        response = {}

        if elb['Type'] == 'network':
            elb_info['associated_waf'] = 'N/A'
        elif elb['Type'] == 'application':
            response = wafv2_client.get_web_acl_for_resource(ResourceArn=elb['LoadBalancerArn'])

        if 'WebACL' in response:
            elb_info['associated_waf'] = response['WebACL']['Name']

        elb_info_list.append(elb_info)

    return elb_info_list


def get_elbv1_info(elb_client, profile_info):
    elbs_v1 = get_all_elbv1_load_balancers(elb_client)

    elb_info_list = []
    for elb in tqdm(elbs_v1):
        elb_info = {
            'sso_session': profile_info['sso_session'],
            'profile_name': profile_info['profile_name'],
            'account_id': profile_info['account_id'],
            'name': elb['LoadBalancerName'],
            'version': 'v1',
            'type': 'classic',
            'scheme': elb['Scheme'],
            'associated_waf': 'N/A',
            'marked_as_waf_ignore': False
        }

        elb_info_list.append(elb_info)

    return elb_info_list


def get_cloudfront_info(cloudfront_client, wafv2_client, profile_info):
    distributions = get_all_cloudfront_distributions(cloudfront_client)

    cloudfront_info_list = []
    for dist in tqdm(distributions):
        distribution_name = dist['Aliases']['Items'][0] if dist['Aliases']['Quantity'] > 0 else dist['DomainName']
        associated_waf = dist['WebACLId'].split('/')[-2] if dist['WebACLId'] != '' else 'None'

        cloudfront_info = {
            'sso_session': profile_info['sso_session'],
            'profile_name': profile_info['profile_name'],
            'account_id': profile_info['account_id'],
            'distribution_id': dist['Id'],
            'distribution_name': distribution_name,
            'associated_waf': associated_waf
        }

        cloudfront_info_list.append(cloudfront_info)
    
    return cloudfront_info_list


def scan_waf_coverage_for_profiles_from_csv(csv_filepath):
    profiles = read_profiles_from_csv(csv_filepath)

    elb_info_list = []
    cloudfront_info_list = []
    for profile_info in profiles:
        session = boto3.Session(profile_name=profile_info['profile_name'])
        wafv2_client = session.client('wafv2')
        elbv2_client = session.client('elbv2')
        elb_client = session.client('elb')
        cloudfront_client = session.client('cloudfront')

        print(f"Scanning profile: {profile_info['profile_name']}")
        elb_info_list.extend(get_elbv2_info(elbv2_client, wafv2_client, profile_info))
        elb_info_list.extend(get_elbv1_info(elb_client, profile_info))
        cloudfront_info_list.extend(get_cloudfront_info(cloudfront_client, wafv2_client, profile_info))

    return { 'elb': elb_info_list, 'cloudfront': cloudfront_info_list }


if __name__ == '__main__':
    waf_coverage = scan_waf_coverage_for_profiles_from_csv(input_csv_filepath)

    if waf_coverage['elb']:
        with open(elb_csv_filepath, mode='w', newline='') as file:
            fieldnames = waf_coverage['elb'][0].keys()
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(waf_coverage['elb'])

    if waf_coverage['cloudfront']:
        with open(cloudfront_csv_filepath, mode='w', newline='') as file:
            fieldnames = waf_coverage['cloudfront'][0].keys()
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(waf_coverage['cloudfront'])
