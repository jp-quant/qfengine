from qfengine.data.vendor_api.IEX.iex_cloud import IEX, IEXSandbox
import os


os.environ["IEX_API_VERSION"] = "iexcloud-sandbox"
os.environ["IEX_OUTPUT_FORMAT"] = "pandas"



'''
os.environ["IEX_TOKEN"] = open(
                            os.path.join(
                                        os.path.dirname(os.path.realpath(__file__)),
                                        "api_key.txt"
                                        )
                              ).read().split("\n")[0]

os.environ["IEX_API_VERSION"] = "iexcloud-v1"
os.environ["IEX_OUTPUT_FORMAT"] = "pandas"
'''






info = {
    'name': 'IEX',
    'website_url': 'https://iexcloud.io/',
    'api_endpoint_url': 'https://cloud.iexapis.com/'
}




