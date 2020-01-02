import json
import xbmc

class json_rpc(object):

    id_ = 1
    jsonrpc = "2.0"

    def __init__(self, method, **kwargs):
        
        self.method = method

        for arg in kwargs: # id_(int), jsonrpc(str)
            self.arg = arg

    def _query(self):

        query = {
            
            'jsonrpc': self.jsonrpc,
            'id': self.id_,
            'method': self.method,
        }
        if self.params is not None:
            query['params'] = self.params

        return json.dumps(query)

    def execute(self, params=None):

        self.params = params
        return json.loads(xbmc.executeJSONRPC(self._query()))


def get_value(name):
    result = json_rpc('Settings.getSettingValue').execute({'setting': name})
    return result['result']['value']


def set_value(name, value):
    params = {
        'setting': name,
        'value': value
    }
    result = json_rpc('Settings.setSettingValue').execute(params)
    return result

