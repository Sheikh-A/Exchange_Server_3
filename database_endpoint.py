from flask import Flask, request, g
from flask_restful import Resource, Api
from sqlalchemy import create_engine, select, MetaData, Table
from flask import jsonify
import json
import eth_account
import algosdk
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import load_only

from models import Base, Order, Log
engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

app = Flask(__name__)


#These decorators allow you to use g.session to access the database inside the request code
#BEFORE REQUEST
@app.before_request
def create_session():
    g.session = scoped_session(DBSession) #g is an "application global" https://flask.palletsprojects.com/en/1.1.x/api/#application-globals

@app.teardown_appcontext
def shutdown_session(response_or_exc):
    g.session.commit()
    g.session.remove()

"""
-------- Helper methods (feel free to add your own!) -------
"""

def log_message(content):
    # Takes input dictionary d and writes it to the Log table
    #pass
    #Create a Dictionary
    trade = {}
    #BUYSELL
    trade["buy_currency"] = content["payload"]["buy_currency"]
    trade["sell_currency"] = content["payload"]["sell_currency"]
    #BUYAMT
    trade["buy_amount"] = content["payload"]["buy_amount"]
    trade["sell_amount"] = content["payload"]["sell_amount"]
    #ADDRESS
    trade["sender_pk"] = content["payload"]["sender_pk"]
    trade["receiver_pk"] = content["payload"]["receiver_pk"]
    #PLATFORM
    trade["platform"] = content["payload"]["platform"]

    log_obj = Log( message = json.dumps(trade) )
    g.session.add(log_obj)
    g.session.commit()



"""
---------------- Endpoints ----------------
"""

@app.route('/trade', methods=['POST'])
def trade():
    if request.method == "POST":
        content = request.get_json(silent=True)
        print( f"content = {json.dumps(content)}" )
        columns = [ "sender_pk", "receiver_pk", "buy_currency", "sell_currency", "buy_amount", "sell_amount", "platform" ]
        fields = [ "sig", "payload" ]
        error = False
        for field in fields:
            if not field in content.keys():
                print( f"{field} not received by Trade" )
                print( json.dumps(content) )
                log_message(content)
                return jsonify( False )

        error = False
        for column in columns:
            if not column in content['payload'].keys():
                print( f"{column} not received by Trade" )
                error = True
        if error:
            print( json.dumps(content) )
            log_message(content)
            return jsonify( False )

        #YOUR CODE HERE
        platform = content['payload']['platform']

        # ALGORAND
        if platform == "Algorand" or platform == "algorand":
            sig = content["sig"]
            #Public KEY
            pk = content["payload"]["sender_pk"]

            receiver_pk = content["payload"]["receiver_pk"]

            buy_amount = content["payload"]["buy_amount"]
            sell_amount = content["payload"]["sell_amount"]

            buy_currency = content["payload"]["buy_currency"]
            sell_currency = content["payload"]["sell_currency"]


            trade = {'platform':platform,
                     'sender_pk': pk,
                     'receiver_pk': receiver_pk,
                     'buy_amount':buy_amount,
                     'sell_amount':sell_amount,
                     'buy_currency':buy_currency,
                     'sell_currency': sell_currency,
                     }
            #JSON DUMPS
            payload = json.dumps(trade)

            if algosdk.util.verify_bytes(payload.encode('utf-8'),sig,pk):
                print( "Checked" )

                order_obj = Order(
                    sender_pk=trade['sender_pk'],
                    receiver_pk=trade['receiver_pk'],
                    #BUYAMT
                    buy_amount=trade['buy_amount'],
                    sell_amount=trade['sell_amount'],
                    #BUYCURR
                    buy_currency=trade['buy_currency'],
                    sell_currency=trade['sell_currency'],
                    #SIG
                    signature = content["sig"] )
                #Add order
                g.session.add(order_obj)
                #commit order
                g.session.commit()
                return jsonify(True)
            #ERROR MESSAGE
            else :
                log_message(content)
                print("error")
                return jsonify(False)
        #ETHEREUM
        elif platform == "Ethereum" or platform == "ethereum":
            sig = content["sig"][2:]
            pk = content["payload"]["sender_pk"]

            receiver_pk = content["payload"]["receiver_pk"]

            buy_amount = content["payload"]["buy_amount"]
            sell_amount = content["payload"]["sell_amount"]

            buy_currency = content["payload"]["buy_currency"]
            sell_currency = content["payload"]["sell_currency"]

            msg_dict = {'platform':platform,'sender_pk': pk, 'receiver_pk': receiver_pk, 'buy_currency':buy_currency,'sell_currency': sell_currency,'sell_amount':sell_amount,'buy_amount':buy_amount}

            message = json.dumps(msg_dict)

            eth_encoded_msg = eth_account.messages.encode_defunct(text=message)
            print('Ethereum public KEY: '+ pk)

            if eth_account.Account.recover_message(eth_encoded_msg,signature=sig) == pk:
                print( "Check completed!" )
                order_obj = Order( sender_pk=pk,receiver_pk=receiver_pk, buy_currency=buy_currency, sell_currency=sell_currency, buy_amount=buy_amount, sell_amount=sell_amount,signature = content["sig"] )
                g.session.add(order_obj)
                g.session.commit()
                return jsonify(True)
            else :
                print('Recovered ETH pk::'+eth_account.Account.recover_message(eth_encoded_msg,signature=sig))
                log_message(content)
                print("Error")
                return jsonify(False)
        else:
            print("Error check code")


@app.route('/order_book')
def order_book():
    #Your code here
    result = g.session.query(Order).all()

    #GET OBJECT RESULT

    json_result = {
    'data': []
    }

    for item in result:
        json_result['data'].append({
            'sender_pk': item.sender_pk,
            'receiver_pk': item.receiver_pk,
            'buy_amount': item.buy_amount,
            'sell_amount': item.sell_amount,
            'buy_currency': item.buy_currency,
            'sell_currency': item.sell_currency,
            'signature': item.signature
            })

    return jsonify(json_result)

if __name__ == '__main__':
    app.run(port='5002')