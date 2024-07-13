import boto3
from tqdm import tqdm

wafv2_client = boto3.client('wafv2')
elbv2_client = boto3.client('elbv2')
elb_client = boto3.client('elb')

# ToDo: avaliar todas as AWS Accounts
# ToDo: avaliar API Gateway e CloudFront
# ToDo: ignorar ELBs com tag especificada

#web_acls = wafv2_client.list_web_acls(Scope='REGIONAL')['WebACLs']

def get_elbv2_info(wafv2_client, elbv2_client):
    elbs_v2 = elbv2_client.describe_load_balancers()['LoadBalancers']

    elbs_info = []
    for elb in tqdm(elbs_v2):
        elb_info = {
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
        elbs_info.append(elb_info)

    return elbs_info


def get_elbv1_info(elb_client):
    elbs_v1 = elb_client.describe_load_balancers()['LoadBalancerDescriptions']

    elbs_info = []
    for elb in tqdm(elbs_v1):
        elb_info = {
            'name': elb['LoadBalancerName'],
            'version': 'v1',
            'type': 'classic',
            'scheme': elb['Scheme'],
            'associated_web_acl': 'N/A'  # Classic ELBs não suportam associação direta com WebACLs
        }

        print(elb_info)
        elbs_info.append(elb_info)

    return elbs_info


if __name__ == '__main__':
    elbsv2_info = get_elbv2_info(wafv2_client, elbv2_client)
    for elb in elbsv2_info:
        print(elb)
    elbsv1_info = get_elbv1_info(elb_client)
    for elb in elbsv1_info:
        print(elb)
