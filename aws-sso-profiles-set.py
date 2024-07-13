import argparse
import configparser
import csv
import os

parser = argparse.ArgumentParser(description='Set AWS SSO profiles from a CSV file.')
parser.add_argument('--sso-role-name', required=True, help='SSO role name to be set for each profile.')
parser.add_argument('--region', default='us-east-1', help='Default AWS region. Default is us-east-1.')
parser.add_argument('--output', default='json', help='Default output format. Default is json.')
parser.add_argument('--input-file', default='workspace/aws_profiles.csv', help='Input CSV file. Default is aws_profiles.csv.')
parser.add_argument('--output-file', default='workspace/aws.config', help='Output AWS config file. Default is aws.config.')

args = parser.parse_args()

input_csv_filepath = os.path.expanduser(args.input_file)
aws_config_filepath = os.path.expanduser(args.output_file)

config = configparser.ConfigParser()

with open(input_csv_filepath, mode='r', newline='') as file:
    reader = csv.DictReader(file)
    for row in reader:
        section_name = f"profile {row['profile_name']}"
        config.add_section(section_name)

        config.set(section_name, 'sso_session', row['sso_session'])
        config.set(section_name, 'sso_account_id', row['account_id'])

        config.set(section_name, 'sso_role_name', args.sso_role_name)
        config.set(section_name, 'region', args.region)
        config.set(section_name, 'output', args.output)

with open(aws_config_filepath, 'w') as file:
    config.write(file)
