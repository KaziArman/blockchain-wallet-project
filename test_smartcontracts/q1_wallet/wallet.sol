// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract BasicWallet {
    address public owner;
    mapping(address => uint256) public balances;
    address[] public depositorList;
    mapping(address => bool) private isDepositor;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }

    // 1. Anyone can deposit any amount of balance in their wallet
    function deposit() public payable {
        require(msg.value > 0, "Deposit must be greater than 0");
        balances[msg.sender] += msg.value;
        if (!isDepositor[msg.sender]) {
            depositorList.push(msg.sender);
            isDepositor[msg.sender] = true;
        }
    }

    // 2 & 3. Only owner can withdraw x% of a specific depositor's balance
    //         and transfer it to the owner's account
    function withdrawFromDepositor(address depositor, uint256 percentage) public onlyOwner {
        require(percentage > 0 && percentage <= 100, "Percentage must be between 1 and 100");
        require(balances[depositor] > 0, "Depositor has no balance");

        uint256 amount = (balances[depositor] * percentage) / 100;
        balances[depositor] -= amount;
        payable(owner).transfer(amount);
    }

    // Owner can withdraw x% from ALL depositors at once
    function withdrawFromAll(uint256 percentage) public onlyOwner {
        require(percentage > 0 && percentage <= 100, "Percentage must be between 1 and 100");

        uint256 totalAmount = 0;
        for (uint256 i = 0; i < depositorList.length; i++) {
            address dep = depositorList[i];
            if (balances[dep] > 0) {
                uint256 amount = (balances[dep] * percentage) / 100;
                balances[dep] -= amount;
                totalAmount += amount;
            }
        }

        if (totalAmount > 0) {
            payable(owner).transfer(totalAmount);
        }
    }

    // 4. Anyone can view their existing balance
    function getBalance(address user) public view returns (uint256) {
        return balances[user];
    }

    // Utility: get number of depositors
    function getDepositorCount() public view returns (uint256) {
        return depositorList.length;
    }

    // Utility: get depositor address by index
    function getDepositor(uint256 index) public view returns (address) {
        require(index < depositorList.length, "Index out of bounds");
        return depositorList[index];
    }

    // Utility: get contract's total ETH held
    function getContractBalance() public view returns (uint256) {
        return address(this).balance;
    }
}
