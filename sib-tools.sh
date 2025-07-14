#!/bin/sh

set -e

set -a
# echo "${#KEYRING_CRYPTFILE_PASSWORD}"
source /etc/sib-tools/keyring-decrypt-password.env
# echo "${#KEYRING_CRYPTFILE_PASSWORD}"
# python -c "
# import keyring
# import os
# from os import getenv

# # kr.keyring_key = os.environ['KEYRING_CRYPTFILE_PASSWORD']
# kr.keyring_key = None
# keyring.set_keyring(kr)
# print('Environment variable set:', 'KEYRING_CRYPTFILE_PASSWORD' in os.environ)
# print(f\"Length: {len(os.environ['KEYRING_CRYPTFILE_PASSWORD'])}\")

# if KEYRING_CRYPTFILE_PASSWORD in os.environ:
#     from keyrings.cryptfile.cryptfile import CryptFileKeyring
#     kr = CryptFileKeyring()
#     self.keyring_key = os.environ[KEYRING_CRYPTFILE_PASSWORD]
#     keyring.set_keyring(kr)

# # Try to set a password to initialize the keyring
# try:
#     keyring.set_password('test-init', 'user', 'password')
#     print('Keyring initialized successfully!')
#     # Test retrieval
#     retrieved = keyring.get_password('test-init', 'user')
#     print('Retrieved password:', retrieved)
# except Exception as e:
#     print('Error:', e)
#     import traceback
#     traceback.print_exc()
# "

# python -c "
# import keyring
# import os
# print('Current keyring:', keyring.get_keyring())
# print('Keyring class:', type(keyring.get_keyring()).__name__)
# print('KEYRING_CRYPTFILE_PASSWORD set:', 'KEYRING_CRYPTFILE_PASSWORD' in os.environ)
# if 'KEYRING_CRYPTFILE_PASSWORD' in os.environ:
#     print('Password length:', len(os.environ['KEYRING_CRYPTFILE_PASSWORD']))
# "
# python -c "
# import keyring
# import os
# print('Testing keyring access...')
# try:
#     # Try to access an existing password without prompting
#     result = keyring.get_password('test-service', 'test-user')
#     print('Success! Got password:', result is not None)
# except Exception as e:
#     print('Error accessing keyring:', e)
#     import traceback
#     traceback.print_exc()
# "
set +a
echo "${#KEYRING_CRYPTFILE_PASSWORD}"
python -m sib_tools "$@"
