import argparse
import configparser
import csv
import os

parser = argparse.ArgumentParser(description='Set AWS SSO profiles from a CSV file.')
parser.add_argument('--input-file', default='~/.aws/config', help='Input AWS config file. Default is ~/.aws/config.')
parser.add_argument('--output-file', default='workspace/aws_profiles.csv', help='Output CSV file. Default is aws_profiles.csv.')

args = parser.parse_args()

aws_config_filepath = os.path.expanduser(args.input_file)
output_csv_filepath = os.path.expanduser(args.output_file)

config = configparser.ConfigParser()
config.read(aws_config_filepath)

with open(output_csv_filepath, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['sso_session', 'profile_name', 'account_id'])

    for section in config.sections():
        if not section.startswith('profile '):
            continue

        profile_name = section.replace('profile ', '')
        sso_session = config.get(section, 'sso_session', fallback='Unknown')

        if sso_session != 'Unknown':
            account_id = config.get(section, 'sso_account_id')
            writer.writerow([sso_session, profile_name, account_id])
