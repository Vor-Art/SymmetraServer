# Replace with a database in production
database = {
    'users': {
        'admin': {
            'pass': 'admin',
            'role': 'admin'
        },
        'user': {
            'pass': 'pass',
            'role': 'client'
        },
    }
}
# print(database['users'].keys())
print(database['users']['user']['pass'])

