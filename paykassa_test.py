import requests
from paykassa.payment import PaymentApi
from paykassa.merchant import MerchantApi
passw = "gnLH9xPXJWCrYLsiuSGo7DOdYMJbGhLf"
client = MerchantApi("22645", passw)
client_api = PaymentApi(24014, "K78myX14gLUUOoODJ6anqN4CiT9mGPbj")
from paykassa.dto import GenerateAddressRequest, GetPaymentUrlRequest, CheckTransactionRequest, CheckPaymentRequest, \
    MakePaymentRequest
from paykassa.struct import System, Currency, CommissionPayer

pay_req = MakePaymentRequest().set_amount(str(123)).set_system(System.BERTY).set_currency(Currency.USD).set_test(True).set_number("3LPnTCZFWdHRUC3imeyPsFEeAV68Qkpw9E")
print(client_api.make_payment(pay_req).get_message())

request = GetPaymentUrlRequest() \
    .set_amount("1.23") \
    .set_currency(Currency.DOGE) \
    .set_system(System.DOGECOIN) \
    .set_comment("test") \
    .set_paid_commission(CommissionPayer.CLIENT)\
    .set_order_id("")\
    .set_test(True)

response = client.generate_address(request)

if not response.has_error():
    print(response.get_amount())
    print(response.get_wallet())

response = client.get_payment_url(request)
if not response.has_error():
    hash = response.get_params()["hash"]

    request = CheckPaymentRequest() \
        .set_private_hash("474c56752815e3b862224c1c19cdfb39f68abe163a452d119524f327f9b9adc")\

    response = client.check_payment(request)

    if not response.has_error():
        print(response.get_transaction())