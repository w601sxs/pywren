import pywrencli
import click
import os
import boto3
import botocore
import pywren.wrenconfig
import pwd
import random
import time

def get_username():
    return pwd.getpwuid( os.getuid() )[ 0 ]

def click_validate_prompt(message, default, validate_func, fail_msg =""):
    """
    Click wrapper that repeats prompt until acceptable answer
    """
    while True:
        res = click.prompt(message, default)
        if validate_func(res):
            return res
        else:
            if fail_msg != "":
                click.echo(fail_msg.format(res))

def check_aws_region_valid(aws_region_str):
    if aws_region_str in ['us-west-2']:
        return True
    return False

def check_overwrite_function(filename):
    filename = os.path.expanduser(filename)
    if os.path.exists(filename):
        return click.confirm("{} already exists, would you like to overwrite?".format(filename))
    return True

def check_bucket_exists(s3bucket):
    """
    This is the recommended boto3 way to check for bucket
    existence:
    http://boto3.readthedocs.io/en/latest/guide/migrations3.html
    """
    s3 = boto3.resource("s3")
    exists = True
    try:
        s3.meta.client.head_bucket(Bucket=s3bucket)
    except botocore.exceptions.ClientError as e:
        # If a client error is thrown, then check that it was a 404 error.
        # If it was a 404 error, then the bucket does not exist.
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            exists = False
        else:
            raise e
    return exists

def create_unique_bucket_name():
    bucket_name = "{}-pywren-{}".format(get_username(), 
                                        random.randint(0, 999))
    return bucket_name

def check_valid_bucket_name(bucket_name):
    # FIXME check if it is a valid bucket name
    # and if we can write to it and read from it
    return True
    
def validate_s3_prefix(prefix):
    # FIXME
    return True

def validate_lambda_function_name(function_name):
    # FIXME
    return True

def validate_lambda_role_name(role_name):
    # FIXME
    return True

@click.command()
@click.pass_context
def interactive_setup(ctx):

    click.echo("This is the pywren interactive setup script")
    try:
        #first we will try and make sure AWS is set up

        account_id = ctx.invoke(pywrencli.get_aws_account_id, False)
        click.echo("Your AWS configuration appears to be set up, and your account ID is {}".format(account_id))
    except Exception as e:
        raise

    click.echo("This interactive script will set up your initial pywren configuration.")
    click.echo("If this is your first time using pywren then accepting the defaults should be fine")
    
    # first, what is your default AWS region? 
    aws_region = click_validate_prompt("What is your default aws region?", 
                                 default=pywren.wrenconfig.AWS_REGION_DEFAULT, 
                                 validate_func = check_aws_region_valid, 
                                 fail_msg = "{} not a valid aws region")
    # FIXME make sure this is a valid region
    
    
    # if config file exists, ask before overwriting
    config_filename = click_validate_prompt("Location for config file: ", 
                                            default=pywren.wrenconfig.get_default_home_filename(), 
                                            validate_func=check_overwrite_function)
    config_filename = os.path.expanduser(config_filename)

    s3_bucket = click_validate_prompt("pywren requires an s3 bucket to store intermediate data. What s3 bucket would you like to use?", 
                                      default=create_unique_bucket_name(), validate_func=check_valid_bucket_name)
    create_bucket = False
    if not check_bucket_exists(s3_bucket):                                        
        create_bucket = click.confirm("Bucket does not currently exist, would you like to create it?", default=True)

    click.echo("Pywren prefixes every object it puts in S3 with a particular prefix")
    bucket_pywren_prefix = click_validate_prompt("pywren s3 prefix: ", 
                                                 default=pywren.wrenconfig.AWS_S3_PREFIX_DEFAULT, 
                                                 validate_func=validate_s3_prefix)

    lambda_config_advanced = click.confirm("Would you like to configure advanced PyWren properties?", default=False)
    lambda_role = pywren.wrenconfig.AWS_LAMBDA_ROLE_DEFAULT
    function_name = pywren.wrenconfig.AWS_LAMBDA_FUNCTION_NAME_DEFAULT

    if lambda_config_advanced:
        lambda_role = click_validate_prompt("Each lambda function runs as a particular"
                                          "IAM role. What is the name of the role you"
                                          "would like created for your lambda", 
                                          default=pywren.wrenconfig.AWS_LAMBDA_ROLE_DEFAULT, 
                                          validate_func = validate_lambda_role_name)
        function_name = click_validate_prompt("Each lambda function has a particular"
                                              "What would you like to name yours?",
                                              default=pywren.wrenconfig.AWS_LAMBDA_FUNCTION_NAME_DEFAULT, 
                                              validate_func = validate_lambda_function_name)
    click.echo("pywren standalone mode uses dedicated AWS instances to run pywren tasks. This is more flexible, but more expensive with fewer simultaneous workers.")
    use_standalone = click.confirm("Would you like to enable pywren standalone mode?")

    click.echo("Creating config {}".format(config_filename))
    ctx.obj = {"config_filename" : config_filename}
    ctx.invoke(pywrencli.create_config, 
               aws_region = aws_region, 
               bucket_name = s3_bucket, 
               lambda_role = lambda_role, 
               function_name = function_name,
               bucket_prefix= bucket_pywren_prefix, 
               force=True)
    if create_bucket:
        click.echo("Creating bucket {}".format(s3_bucket))
        ctx.invoke(pywrencli.create_bucket)
    click.echo("Creating role")
    ctx.invoke(pywrencli.create_role)
    click.echo("deploying lambda")
    ctx.invoke(pywrencli.deploy_lambda)

    if use_standalone:
        click.echo("setting up standalone mode")
        ctx.invoke(pywrencli.create_queue)
        ctx.invoke(pywrencli.create_instance_profile)
    click.echo("pausing for 10 sec for changes to propoagate")
    time.sleep(10)
    ctx.invoke(pywrencli.test_function)

if __name__ == '__main__':
    interactive_setup()
