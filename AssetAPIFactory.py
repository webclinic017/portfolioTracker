import requests
from yahoofinancials import YahooFinancials

class AssetAPIFactory:
    cachedPrices = {}
    def __init__(self, logging):
        self.logging = logging

    def getPriceUSD(self, ticker):
        if ticker in self.cachedPrices:
            self.logging.debug("using cache for " + ticker)
            return self.cachedPrices[ticker]

        elif ticker == "AAPL" or ticker == "VUG" or ticker == "GME" or ticker == "VOO" or ticker == "BRK-B":
            yahoo_financials = YahooFinancials(ticker)
            self.cachedPrices[ticker] = YahooFinancials([ticker]).get_current_price()[ticker]
            return self.cachedPrices[ticker]
        elif ticker == "VIX":
            self.cachedPrices[ticker] = YahooFinancials(['^VIX']).get_current_price()['^VIX']
            return self.cachedPrices[ticker]
        elif ticker == "BTC" or  ticker == "ETH":
            TICKER_API_URL = 'https://www.bitstamp.net/api/v2/ticker/' + ticker.lower() + "usd/"
            response = requests.get(TICKER_API_URL)
            response_json = response.json()
            self.cachedPrices[ticker] = float(response_json['last'])
            return self.cachedPrices[ticker]

    def USCurrency(self, ticker):
        #if ticker in [""]:
         #   return False
        #else:
            return True

    def getExchangeRate(self):
        if not hasattr(self, 'exchangeRate'):
            API = 'http://api.exchangeratesapi.io/latest?access_key=c65663c506bc6d16fe81766cadde9918'
            response = requests.get(API)
            response_json = response.json()
            aud = response_json["rates"]['AUD']
            usd = response_json["rates"]['USD']
            self.exchangeRate = float(aud / usd)
        return self.exchangeRate
    def clear(self):
        self.cachedPrices = {}
