# Python Scripts

## AWS

### aws-sso-profiles-get.py

This script will get all the AWS SSO profiles from the AWS CLI configuration file and create a CSV with:

- SSO session name
- Profile name
- Account ID

This information can be used in other scripts to create others AWS CLI configuration file or to scripts that need to assume roles in multiple accounts.

### aws-sso-profiles-set.py

This script will set the AWS SSO profiles in the AWS CLI configuration file. The profiles are read from a CSV file with the following columns:

- SSO session name
- Profile name
- Account ID

With this script, you can create a AWS CLI configuration file writing just a few information in a CSV file instead of writing the whole configuration file. And the CSV file can be shared with other team members.

It's useful define standard profiles names, like slugs for each AWS account. This slugs can be used in other parts of the infrastructure, like Pulumi or Terraform.

### waf-coverage-get-info.py

This script will get informations from entrypoints like CloudFront, ELB, API Gateway and check if they are protected by WAF. Each of this entrypoints will have specific properties to indicate version, type, if it's private or public, etc. All of this entrypoints will have the following properties:

- SSO session name: this can indicate the AWS Organization
- Profile prefix: this can indicate some logicial separation, like environment (dev, stage, prod) ou business unit
- Profile name: this can indicate the AWS account in a more human readable way
- Account ID: this indicate the AWS account
- Associated WAF: this indicate if the entrypoint is protected by WAF and which is the WAF name
- WAF version: this indicate the WAF version
- Marked as WAF ignore: this indicate if the entrypoint is marked as WAF ignore

### waf-coverage-calculate.py

This script will calculate the WAF coverage based on the informations from the `waf-coverage-get-info.py` script. The coverage will be calculated based on the number of entrypoints instead of the number of requests. The WAF is charged based on the number of requests, so add more entrypoints with low use will not increase the cost of the WAF and help to reduce the attack surface.

The rules to calculate the coverage are opinionated and cannot be the best for all cases.
