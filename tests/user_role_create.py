import boto3
import botocore.errorfactory
import time


def total_delete_user(iam, username):
    u = iam.User(username)
    u.load()
    for k in u.access_keys.all():
        k.delete()
    for p in u.policies.all():
        p.delete()

    print "deleting user", u
    u.delete()
    print "user deleted" 

def test():

    iam = boto3.resource('iam')

    username = 'programmatic_test_user'

    try:
        total_delete_user(iam, username)
        time.sleep(5)
    except botocore.errorfactory.ClientError as e:
        print "ERROR", e
        pass
    
    new_user = iam.create_user(UserName=username)
    access_key_pair = new_user.create_access_key_pair()
    print "new user created", access_key_pair
    policy_str = open('default_pywren_user_permissions.json', 'r').read()
    new_user.create_policy(PolicyName='test_policy', 
                           PolicyDocument = policy_str)
    time.sleep(10)


    user_session = boto3.session.Session(aws_access_key_id=access_key_pair.id, 
                                    aws_secret_access_key=access_key_pair.secret)

    user_s3 = user_session.resource('s3')
    for b in user_s3.buckets.all():
        print b

    print "after new users"
    for user in iam.users.all():
        print user
    total_delete_user(iam, username)

if __name__ == "__main__":
    test()
