import argparse
import csv
import os
from collections import defaultdict
from tabulate import tabulate

parser = argparse.ArgumentParser(description='Set AWS SSO profiles from a CSV file.')
parser.add_argument('--input-file', default='workspace/waf_coverage.csv', help='Input CSV file. Default is aws_profiles.csv.')
parser.add_argument('--debug', action='store_true', help='Print debug table.')

args = parser.parse_args()

input_csv_filepath = os.path.expanduser(args.input_file)
input_file_path, input_file_extension = os.path.splitext(args.input_file)
elb_csv_filepath = os.path.expanduser(f'{input_file_path}_for_elb{input_file_extension}')
cloudfront_csv_filepath = os.path.expanduser(f'{input_file_path}_for_cloudfront{input_file_extension}')
apigw_csv_filepath = os.path.expanduser(f'{input_file_path}_for_apigw{input_file_extension}')


def calculate_waf_coverage(resources):
    total_resources = resources['total_resources']
    waf_resources = resources['waf_resources']
    coverage_results = {}

    for profile_prefix in total_resources:
        total_count = total_resources[profile_prefix]
        waf_count = waf_resources.get(profile_prefix, 0)

        percentage = (waf_count / total_count) * 100
        coverage_results[profile_prefix] = f"{percentage:.2f}%"

    return coverage_results


def count_cloudfront_with_waf(csv_file_path):
    total_resources = defaultdict(int)
    waf_resources = defaultdict(int)

    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            total_resources[row['profile_prefix']] += 1

            # This rule is explicit to serve as documentation, but it is the same as row['waf_version'] == 'v2'
            if row['waf_version'].lower() == 'v1' or row['associated_waf'].lower() == 'none':
                continue

            waf_resources[row['profile_prefix']] += 1

    return { 'total_resources': total_resources, 'waf_resources': waf_resources }


def count_elb_with_waf(csv_file_path):
    total_resources = defaultdict(int)
    waf_resources = defaultdict(int)

    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row['marked_as_waf_ignore'].lower() == 'true' or row['scheme'].lower() == 'internal' or row['type'].lower() == 'network':
                continue

            total_resources[row['profile_prefix']] += 1

            # This rule is explicit to serve as documentation, but it is the same as row['waf_version'] == 'v2'
            if row['type'].lower() == 'classic' or row['waf_version'].lower() == 'v1' or row['associated_waf'].lower() == 'none':
                continue

            waf_resources[row['profile_prefix']] += 1

    return { 'total_resources': total_resources, 'waf_resources': waf_resources }


def count_apigw_with_waf(csv_file_path):
    total_resources = defaultdict(int)
    waf_resources = defaultdict(int)

    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row['endpoint_type'].lower() == 'private':
                continue

            total_resources[row['profile_prefix']] += 1

            # This rule is explicit to serve as documentation, but it is the same as row['waf_version'] == 'v2'
            if row['protocol'].lower() == 'http' or row['waf_version'].lower() == 'v1' or row['associated_waf'].lower() == 'none':
                continue

            waf_resources[row['profile_prefix']] += 1

    return { 'total_resources': total_resources, 'waf_resources': waf_resources }


def generate_profile_prefixes(*resources):
    profile_prefixes = set()
    for resource in resources:
        profile_prefixes |= set(resource['total_resources'].keys())
    
    return profile_prefixes


def summarize_waf_info(cloudfront_resources, elb_resources, apigw_resources):
    combined_resources = {
        'total_resources': defaultdict(int),
        'waf_resources': defaultdict(int),
    }
    profile_prefixes = generate_profile_prefixes(cloudfront_resources, elb_resources, apigw_resources)
    
    for profile_prefix in profile_prefixes:
        combined_resources['total_resources'][profile_prefix] = \
            cloudfront_resources['total_resources'].get(profile_prefix, 0) + \
            elb_resources['total_resources'].get(profile_prefix, 0) + \
            apigw_resources['total_resources'].get(profile_prefix, 0)

        combined_resources['waf_resources'][profile_prefix] = \
            cloudfront_resources['waf_resources'].get(profile_prefix, 0) + \
            elb_resources['waf_resources'].get(profile_prefix, 0) + \
            apigw_resources['waf_resources'].get(profile_prefix, 0)
    
    return combined_resources


def print_debug_table(summarized_resources, cloudfront_resources, elb_resources, apigw_resources):
    combined_resources = {}
    profile_prefixes = summarized_resources['total_resources'].keys()
    for profile_prefix in profile_prefixes:
        combined_resources[profile_prefix] = {
        'CloudFront: Total': cloudfront_resources['total_resources'].get(profile_prefix, 0),
        'CloudFront: WAF': cloudfront_resources['waf_resources'].get(profile_prefix, 0),
        'ELB: Total': elb_resources['total_resources'].get(profile_prefix, 0),
        'ELB: WAF': elb_resources['waf_resources'].get(profile_prefix, 0),
        'API Gateway: Total': apigw_resources['total_resources'].get(profile_prefix, 0),
        'API Gateway: WAF': apigw_resources['waf_resources'].get(profile_prefix, 0),
        'Summarized: Total': summarized_resources['total_resources'].get(profile_prefix, 0),
        'Summarized: WAF': summarized_resources['waf_resources'].get(profile_prefix, 0),
    }

    headers = [
        'Profile Prefix',
        'CloudFront: Total',
        'CloudFront: WAF',
        'ELB: Total',
        'ELB: WAF',
        'API Gateway: Total',
        'API Gateway: WAF',
        'Summarized: Total',
        'Summarized: WAF'
    ]
    table_data = [[profile_prefix] + list(stats.values()) for profile_prefix, stats in combined_resources.items()]

    print()
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    print()


def print_coverage_table(summarized_resources, cloudfront_coverage, elb_coverage, apigw_coverage):
    combined_resources = {}
    profile_prefixes = summarized_resources['total_resources'].keys()
    for profile_prefix in profile_prefixes:
        combined_resources[profile_prefix] = {
        'CloudFront': cloudfront_coverage.get(profile_prefix, 'N/A'),
        'ELB': elb_coverage.get(profile_prefix, 'N/A'),
        'API Gateway': apigw_coverage.get(profile_prefix, 'N/A'),
        'Summarized': summarized_coverage.get(profile_prefix, 'N/A'),
    }

    headers = ['Profile Prefix', 'CloudFront', 'ELB', 'API Gateway', 'Summarized']
    table_data = [ [profile_prefix] + list(stats.values()) for profile_prefix, stats in combined_resources.items()]

    print(tabulate(table_data, headers=headers, tablefmt='grid'))


if __name__ == '__main__':
    cloudfront_resources = count_cloudfront_with_waf(cloudfront_csv_filepath)
    elb_resources = count_elb_with_waf(elb_csv_filepath)
    apigw_resources = count_apigw_with_waf(apigw_csv_filepath)

    summarized_resources = summarize_waf_info(cloudfront_resources, elb_resources, apigw_resources)

    if args.debug:
        print_debug_table(summarized_resources, cloudfront_resources, elb_resources, apigw_resources)

    cloudfront_coverage = calculate_waf_coverage(cloudfront_resources)
    elb_coverage = calculate_waf_coverage(elb_resources)
    apigw_coverage = calculate_waf_coverage(apigw_resources)
    summarized_coverage = calculate_waf_coverage(summarized_resources)

    print_coverage_table(summarized_resources, cloudfront_coverage, elb_coverage, apigw_coverage)
