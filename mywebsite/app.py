# app.py
from flask import Flask, jsonify
from flask_cors import CORS, cross_origin
import module

app = Flask(__name__)
CORS(app, resources={r"*": {"origins": "*"}}) 

@app.route("/get_decks", methods=['GET'])
@cross_origin()
def get_decks():
    username = request.args.get('username')
    decks = module.get_decks(username)
    return jsonify(decks)


@app.route('/process_decks', methods=['POST'])
def process_decks():
    decks = request.get_json()
    EvaluatedGraphs = module.process_decks(decks)
    return jsonify(EvaluatedGraphs)

if __name__ == '__main__':
    app.run(port=5000)
