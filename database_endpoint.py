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
    print('Log_message Function')
    
    #Create a trading Dictionary
    trading = {}
    trading['sender_pk'] = content["payload"]["sender_pk"]
    trading['receiver_pk'] = content["payload"]["receiver_pk"]
    trading['buy_currency'] = content["payload"]["buy_currency"]
    trading['sell_currency'] = content["payload"]["sell_currency"]
    trading['buy_amount'] = content["payload"]["buy_amount"]
    trading['sell_amount'] = content["payload"]["sell_amount"]
    trading['platform'] = content["payload"]["platform"]

    log_obj = Log( message = json.dumps(trading) )
    g.session.add(log_obj)
    g.session.commit()

    

"""
---------------- Endpoints ----------------
"""
    
@app.route('/trading', methods=['POST'])
def trading():
    if request.method == "POST":
        content = request.get_json(silent=True)
        print( f"content = {json.dumps(content)}" )
        columns = [ "sender_pk", "receiver_pk", "buy_currency", "sell_currency", "buy_amount", "sell_amount", "platform" ]
        fields = [ "sig", "payload" ]
        error = False
        for field in fields:
            if not field in content.keys():
                print( f"{field} not received by Trading" )
                print( json.dumps(content) )
                log_message(content)
                return jsonify( False )
        
        error = False
        for column in columns:
            if not column in content['payload'].keys():
                print( f"{column} not received by Trading" )
                error = True
        if error:
            print( json.dumps(content) )
            log_message(content)
            return jsonify( False )
            
        #Your code here
        #Note that you can access the database session using g.session
        #JSON Decoder
        platform = content["payload"]["platform"]

        #Check if signature is valid

        # Ethereum
        if platform == "Ethereum":
            
            sig = content["sig"][2:]
            pk = content["payload"]["sender_pk"]
            
            receiver_pk = content["payload"]["receiver_pk"]
            buy_currency = content["payload"]["buy_currency"]
            sell_currency = content["payload"]["sell_currency"]
            buy_amount = content["payload"]["buy_amount"]
            sell_amount = content["payload"]["sell_amount"]

            #Trading Dict
            msg_dict = {'platform':platform,'sender_pk': pk, 'receiver_pk': receiver_pk, 'buy_currency':buy_currency,'sell_currency': sell_currency,'sell_amount':sell_amount,'buy_amount':buy_amount}
            
            
            message = json.dumps(msg_dict)
            
            eth_encoded_msg = eth_account.messages.encode_defunct(text=message)
            # sk = b'o$\xa6\xe4\xa3\xdc\x91\xbf9\x04\xa0\xc8\x82\xd5\xecz\xa90\x9e]7\xce`no\x1b\x19,\x0b\xb1\x9b\x16'            
            # eth_sig_obj = eth_account.Account.sign_message(eth_encoded_msg,sk)
            # sig = eth_sig_obj.signature.hex()
            # print('signed sig is: '+ sig)
            print('ETH original pk is: '+ pk)

            if eth_account.Account.recover_message(eth_encoded_msg,signature=sig) == pk:   
                print( "Eth sig verifies!" )
                # Write to Order table, exclude platform
                order_obj = Order( sender_pk=pk,receiver_pk=receiver_pk, buy_currency=buy_currency, sell_currency=sell_currency, buy_amount=buy_amount, sell_amount=sell_amount,signature = content["sig"] )
                g.session.add(order_obj)
                g.session.commit()
                return jsonify(True)
            else :
                print('ETH recovered pk is: '+eth_account.Account.recover_message(eth_encoded_msg,signature=sig))
                log_message(content)
                return jsonify(False)
            
        elif platform == "Algorand":
            
            sig = content["sig"]
            pk = content["payload"]["sender_pk"]
            
            
            receiver_pk = content["payload"]["receiver_pk"]
            buy_currency = content["payload"]["buy_currency"]
            sell_currency = content["payload"]["sell_currency"]
            buy_amount = content["payload"]["buy_amount"]
            sell_amount = content["payload"]["sell_amount"]


            #Trading Dict
            trading = {'platform':platform,'sender_pk': pk, 'receiver_pk': receiver_pk, 'buy_currency':buy_currency,'sell_currency': sell_currency,'buy_amount':buy_amount,'sell_amount':sell_amount }
            
            payload = json.dumps(trading)
            
            
            if algosdk.util.verify_bytes(payload.encode('utf-8'),sig,pk):
                print( "Algo sig verifies!" )
                # Write to Order table, exclude platform
                order_obj = Order( sender_pk=trading['sender_pk'],receiver_pk=trading['receiver_pk'], buy_currency=trading['buy_currency'], sell_currency=trading['sell_currency'], buy_amount=trading['buy_amount'], sell_amount=trading['sell_amount'],signature = content["sig"] )
                g.session.add(order_obj)
                g.session.commit()
                return jsonify(True)
            else :               
                log_message(content)
                return jsonify(False)

@app.route('/order_book')
def order_book():
    #Your code here
    #Note that you can access the database session using g.session
    result = g.session.query(Order).all()
    json_obj_result = {
    "data": []
    }

    for row in result:
        # timestamp_str = str(row.timestamp)
        json_obj_result['data'].append({'sender_pk': row.sender_pk,'receiver_pk': row.receiver_pk, 'buy_currency': row.buy_currency, 'sell_currency': row.sell_currency, 'buy_amount': row.buy_amount, 'sell_amount': row.sell_amount,'signature': row.signature})

    return jsonify(json_obj_result)

if __name__ == '__main__':
    app.run(port='5002')