import os
import sys
sys.path.insert(0, 'backend')
sys.path.insert(0, '.')

from app.services.data_source_service import _build_conn_string_from_source

# Test with source like what's stored in the DB
source = {'db_type': 'sqlite', 'db_name': 'dev.db', 'username': '', 'host': '', 'port': None}
result = _build_conn_string_from_source(source, '')
print('Built conn_string for dev.db:', result)

source2 = {'db_type': 'sqlite', 'db_name': 'app.db', 'username': '', 'host': '', 'port': None}
result2 = _build_conn_string_from_source(source2, '')
print('Built conn_string for app.db:', result2)