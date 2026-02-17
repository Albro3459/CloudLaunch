# This is how to check which regions currently support t2.micro

We can only deploy to regions supporting `t2.micro`

Setup your AWS CLI credentials first. 

Sign into the AWS console, go to Security Credentials

Create a CLI access key if you don't have one

In `~/.aws`:

* Create a `credentials` file:
```sh
[cloudlaunch]
aws_access_key_id = AK...
aws_secret_access_key = ...
```

* Create a `config` file:
```sh
[profile cloudlaunch]
source_profile = cloudlaunch
region = us-west-1

[default]
region = us-west-1
```

Run this to get all regions supporting `t2.micro`. Might take a minute.
```sh
for r in $(aws ec2 describe-regions \
  --profile cloudlaunch \
  --query 'Regions[].RegionName' \
  --output text); do

  aws ec2 describe-instance-type-offerings \
    --profile cloudlaunch \
    --region "$r" \
    --location-type region \
    --filters Name=instance-type,Values=t2.micro \
    --query 'InstanceTypeOfferings[].Location' \
    --output text

done
```

Now, update `aws_regions` in `react-frontend/src/helpers/regionsHelper.ts`