pragma solidity ^0.8.0;
contract GlobalAttackDetector {

    address  owner;

    struct RegionAttackProbData {
        uint sigmai;
        uint256 ai0psi;
        uint256 bi0ai;
    }

    uint numRegions; //how many regions or utilities are being considered

    //key-value map with region_id as key and RegionAttackProbData struct as value
    mapping (uint => RegionAttackProbData) apd;

    //constructor function for initialization
    constructor() public {
        owner = msg.sender;
        numRegions = 4;
        for (uint i=0; i<numRegions; i++) {
            apd[i] = RegionAttackProbData(0,1,0);
        }
    }

    //function to onboard new utilities
    function newRegion() public{
      uint regionId = numRegions;
      apd[regionId] = RegionAttackProbData(0,1,0);
      numRegions++;
    }

    // function that allows utilities to communicate their latest local values on the SC
    function setData(uint bi0ai_cap, uint ai0psi_cap, uint sigmai_cap, uint rno) public {

       // current sigma
       apd[rno].sigmai = sigmai_cap;

       // term for global multiplication
       apd[rno].ai0psi = ai0psi_cap;

       // term for global sum
       apd[rno].bi0ai = bi0ai_cap;

    }

    // a read function that delivers the attack stats
    function getGlobalAttackProbability() public returns (uint,uint,uint) {
        // to store total alarms being reported right now
        uint sumsigmai = 0;

        // to store global sum term
        uint256 sumbi0ai = 0;

        //to store global multiplication term
        uint256 multai0psi = 1;

        for (uint i=0; i<numRegions; i++) {

            // global multiplication step
            multai0psi = multai0psi*apd[i].ai0psi;

            //global sum step
            sumbi0ai = sumbi0ai+apd[i].bi0ai;

            //sum update step
            sumsigmai = sumsigmai + apd[i].sigmai;
        }

        return (sumbi0ai,multai0psi,sumsigmai);
    }
}