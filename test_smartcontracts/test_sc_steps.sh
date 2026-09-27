docker compose up test-smartcontracts -d
docker exec -it qbft-network-test-smartcontracts-1 bash -c "python add_peer.py 8546 enode://6ff7f6d92dab07df7ad93a42f2ebcc65f161b9dca8ad6b17607d79026c15a0e51b62c5138a2f1df747ee437f0902052f73f6bb4b31bf187aee5ab6389b3f9baf@10.227.86.209:30303"
docker exec -it qbft-network-test-smartcontracts-1 bash -c "python compile_SC_qbft.py 0 8546"

#if bootnode
curl -X POST --data '{"jsonrpc":"2.0","method":"qbft_proposeValidatorVote","params":["0xd1eaa261df19f8adad634dded3c5a4cb0eefbe4b", true], "id":1}' http://127.0.0.1:8545

#if not bootnode
curl -X POST --data '{"jsonrpc":"2.0","method":"qbft_proposeValidatorVote","params":["0xd1eaa261df19f8adad634dded3c5a4cb0eefbe4b", true], "id":1}' http://127.0.0.1:8546

