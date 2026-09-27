docker exec -it qbft-network-test-smartcontracts-1 python3 -c "
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

web3 = Web3(Web3.HTTPProvider('http://host.docker.internal:8545'))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
print(f'Connected: {web3.is_connected()}')
print(f'Block: {web3.eth.block_number}')

acct = web3.eth.account.create()
jay_addr = Web3.to_checksum_address('0xfe3b557e8fb62b89f4916b721be55ceb828dbd73')
jay_key = '0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63'
new_addr = Web3.to_checksum_address(acct.address)

tx = {
    'from': jay_addr,
    'to': new_addr,
    'value': Web3.to_wei(100, 'ether'),
    'nonce': web3.eth.get_transaction_count(jay_addr),
    'gas': 21000,
    'gasPrice': 0,
}
signed = web3.eth.account.sign_transaction(tx, jay_key)
tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

print(f'Address:     {acct.address}')
print(f'Private Key: {acct.key.hex()}')
bal = web3.eth.get_balance(new_addr)
print(f'Balance:     {Web3.from_wei(bal, \"ether\")} ETH')
print(f'Tx Block:    #{receipt.blockNumber}')
"