
import time
import razorpay
from django.conf import settings
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

class RazorpayClient:

    
    def __init__(self):
        self.key_id = getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_xxxx')
        self.key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', 'xxxx')
        
        self.is_mock = 'xxxx' in self.key_id or not self.key_secret or self.key_secret == 'xxxx'
        
        if not self.is_mock:
            self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
            self._configure_client_session()
        else:
            print("⚠️ WARNING: Running in MOCK PAYMENT MODE. No real transactions will occur.")
    
    def _configure_client_session(self):

        try:
            if hasattr(self.client, 'session'):
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["POST", "GET"]
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                self.client.session.mount("https://", adapter)
                self.client.session.mount("http://", adapter)
                logger.info("✅ Razorpay client session configured with retry strategy")
        except Exception as e:
            logger.warning(f"⚠️ Could not configure Razorpay session: {e}")
    
    def create_order(self, amount, currency="INR", receipt="receipt", notes=None):

        data = {
            "amount": int(amount * 100),  
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1  
        }
        

        if notes:
            data["notes"] = notes
        
        logger.info(
            f"💳 [RAZORPAY_ORDER] Creating order: Amount={amount} {currency} | "
            f"Receipt={receipt} | Mock={self.is_mock}"
        )
        
        if self.is_mock:

            order_id = f"order_mock_{int(time.time())}"
            logger.info(f"🎭 [RAZORPAY_ORDER_MOCK] Mock order created: {order_id}")
            return {
                'success': True,
                'is_mock': True,
                'order_id': order_id,
                'amount': int(amount * 100),
                'currency': currency,
                'receipt': receipt
            }

        max_retries = 5
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                logger.info(f"💳 [RAZORPAY_ORDER] Attempt {retry_count + 1}/{max_retries}")

                order = self.client.order.create(data=data)
                logger.info(
                    f"✅ [RAZORPAY_ORDER] Order created successfully: {order['id']} | "
                    f"Amount: {order['amount']} | Status: {order.get('status', 'created')}"
                )
                return {
                    'success': True,
                    'is_mock': False,
                    'order_id': order['id'],
                    'amount': order['amount'],
                    'currency': order['currency'],
                    'receipt': order['receipt']
                }
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                
                if retry_count < max_retries:

                    wait_time = 2 ** (retry_count - 1)
                    logger.warning(
                        f"⚠️  [RAZORPAY_ORDER] API error (attempt {retry_count}/{max_retries}): {last_error}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"❌ Razorpay API failed after {max_retries} attempts: {last_error}"
                    )
        
        return {
            'success': False,
            'error': f"Payment gateway temporarily unavailable. Please try again in a moment. ({last_error})"
        }
    
    def verify_payment_signature(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return False
        
        if self.is_mock:
            logger.info(f"🎭 [RAZORPAY_SIGNATURE] Mock verification successful")
            return True

        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:

            self.client.utility.verify_payment_signature(params_dict)
            return True
        except Exception as e:

            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Payment signature verification failed: {str(e)}")
            return False
    
    def fetch_payment(self, payment_id):

        try:
            payment = self.client.payment.fetch(payment_id)
            return payment
        except:
            return None

razorpay_client = RazorpayClient()