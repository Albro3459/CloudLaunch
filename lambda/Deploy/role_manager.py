
# Get or create user vpn count in DynamoDB
def get_user_vpn_count(uid, user_table):
    try:
        response = user_table.get_item(Key={"uuid": uid})
        item = response.get("Item")
        if item:
            return item.get("count", 0)
        else:
            user_table.put_item(Item={"uuid": uid, "count": 0})
            return 0
    except Exception as e:
        print("Error reading user count:", e)
        return 0

# Get max count allowed for a role
def get_max_count_for_role(role, role_table):
    try:
        response = role_table.get_item(Key={"role": role})
        item = response.get("Item")
        return item.get("max_count", 1) if item else 1
    except Exception as e:
        print("Error reading role max count:", e)
        return 1

# Increment user count
def increment_user_count(uid, user_table):
    try:
        user_table.update_item(
            Key={"uuid": uid},
            UpdateExpression="SET #c = if_not_exists(#c, :start) + :inc",
            ExpressionAttributeNames={
                "#c": "count" # count is a reserved keyword
            },
            ExpressionAttributeValues={
                ":start": 0,
                ":inc": 1
            }
        )
    except Exception as e:
        print("Error incrementing user count:", e)