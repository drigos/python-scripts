import boto3
import csv
from tqdm import tqdm

wafv2_client = boto3.client('wafv2')
elbv2_client = boto3.client('elbv2')
elb_client = boto3.client('elb')

# ToDo: receber arquivo de input como argumento na CLI
# ToDo: avaliar API Gateway e CloudFront
# ToDo: ignorar ELBs com tag especificada

#web_acls = wafv2_client.list_web_acls(Scope='REGIONAL')['WebACLs']


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


def get_elbv2_info(wafv2_client, elbv2_client, profile_info):
    elbs_v2 = get_all_elbv2_load_balancers(elbv2_client)

    elb_info_list = []
    for elb in tqdm(elbs_v2):
        elb_info = {
            'sso_session': profile_info['sso_session'],
            'profile_name': profile_info['profile_name'],
            'account_id': profile_info['account_id'],
            'name': elb['LoadBalancerName'],
            'version': 'v2',
            'type': elb['Type'],
            'scheme': elb['Scheme'],
            'associated_web_acl': 'None'
        }

        response = {}

        if elb['Type'] == 'network':
            elb_info['associated_web_acl'] = 'N/A'
        elif elb['Type'] == 'application':
            response = wafv2_client.get_web_acl_for_resource(ResourceArn=elb['LoadBalancerArn'])

        if 'WebACL' in response:
            elb_info['associated_web_acl'] = response['WebACL']['Name']

        print(elb_info)
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
            'associated_web_acl': 'N/A'  # Classic ELBs não suportam associação direta com WebACLs
        }

        print(elb_info)
        elb_info_list.append(elb_info)

    return elb_info_list


def scan_waf_coverage_for_profiles_from_csv(csv_filepath):
    profiles = read_profiles_from_csv(csv_filepath)

    elb_info_list = []
    for profile_info in profiles:
        session = boto3.Session(profile_name=profile_info['profile_name'])
        wafv2_client = session.client('wafv2')
        elbv2_client = session.client('elbv2')
        elb_client = session.client('elb')

        print(f"Scanning ELBs for profile: {profile_info['profile_name']}")
        elb_info_list.extend(get_elbv2_info(wafv2_client, elbv2_client, profile_info))
        elb_info_list.extend(get_elbv1_info(elb_client, profile_info))
    
    return elb_info_list


if __name__ == '__main__':
    waf_coverage = scan_waf_coverage_for_profiles_from_csv('workspace/aws_profiles.csv')
    for elb in waf_coverage:
        print(elb)
    # elbsv2_info = get_elbv2_info(wafv2_client, elbv2_client)
    # for elb in elbsv2_info:
    #     print(elb)
    # elbsv1_info = get_elbv1_info(elb_client)
    # for elb in elbsv1_info:
    #     print(elb)
