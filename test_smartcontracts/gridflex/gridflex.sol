// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
contract GridFlexChain {

    address public admin;

    // Pricing constants (credits per kWh)
    uint256 public constant NORMAL_RATE  = 12;   // grid rate in normal conditions
    uint256 public constant PEAK_RATE    = 14;   // grid rate during peak demand
    uint256 public constant DR_REWARD    = 5;    // tokens per kWh reduced

    enum Role     { UTILITY, PROSUMER, CONSUMER, FLEXIBLE, INDUSTRIAL, CRITICAL }
    enum Priority { NORMAL, HIGH, HIGHEST }


    // DATA STRUCTURES


    struct Node {
        string   name;
        Role     role;
        Priority priority;
        bool     isRegistered;
        uint256  rewardTokens;
        int256   creditBalance;
    }

    struct Trade {
        address seller;
        address buyer;
        uint256 amount;
        uint256 pricePerKwh;   // 0 for sealed feed-in trades
        uint256 roundNum;
        uint8   tradeType;     // 0=P2P  1=GRID_DIST  2=FEEDIN (sealed)
    }

    struct Fulfillment {
        uint256 percentServed;
        bool    isProducer;
        bool    recorded;
    }

    struct RoundData {
        uint256 utilityCapacity;
        uint256 totalP2PTraded;
        uint256 totalUtilityTraded;
        uint256 totalFeedIn;
        uint256 totalDRReduced;
        uint256 totalUnserved;
        uint256 tradeCount;
        bool    settled;
    }


    // STATE


    mapping(address => Node)    public nodes;
    address[]                   public nodeAddresses;
    uint256                     public nodeCount;
    uint256                     public currentRound;

    // --- Round gating ---
    uint256                                          public committeeSize;
    mapping(uint256 => uint256)                      public roundCommitCount;

    // --- Energy commitment (privacy) ---
    mapping(uint256 => mapping(address => bytes32))  public commitments;
    mapping(uint256 => mapping(address => bool))     public hasCommitted;

    // Voluntary dispute-reveal (energy data)
    mapping(uint256 => mapping(address => bool))     public hasRevealed;
    mapping(uint256 => mapping(address => uint256))  public revealedProduced;
    mapping(uint256 => mapping(address => uint256))  public revealedConsumed;

    // --- Feed-in bid commitment (auction fairness) ---
    mapping(uint256 => mapping(address => bytes32))  public bidCommitments;
    mapping(uint256 => mapping(address => bool))     public hasBidCommitted;
    mapping(uint256 => mapping(address => uint256))  public revealedBidPrice;
    mapping(uint256 => mapping(address => bool))     public hasBidRevealed;

    // --- Fulfillment, DR, round data ---
    mapping(uint256 => mapping(address => Fulfillment)) public fulfillments;
    mapping(uint256 => mapping(address => uint256))     public demandReductions;
    mapping(uint256 => RoundData)                        public rounds;
    Trade[]                                              public trades;

    // --- IPFS Audit Trail ---
    mapping(uint256 => string)  public roundAuditCID;

    // --- Dynamic Pricing ---
    mapping(uint256 => bool)    public isPeakRound;
    mapping(uint256 => uint256) public roundGridRate;


    // EVENTS


    event NodeRegistered         (address indexed addr, string name, uint8 role);
    event CommitteeSizeSet       (uint256 size);
    event RoundStarted           (uint256 roundNum, uint256 utilityCapacity);
    event CommitmentSubmitted    (uint256 roundNum, address indexed node);
    event BidCommitmentSubmitted (uint256 roundNum, address indexed node);
    event AllCommitted           (uint256 roundNum);
    event TradeRecorded          (uint256 roundNum, address indexed seller,
                                  address indexed buyer, uint256 amount, uint8 tradeType);
    event SealedCreditsRecorded  (uint256 roundNum, address indexed node, int256 credits);
    event FulfillmentRecorded    (uint256 roundNum, address indexed node, uint256 percentServed);
    event DemandResponseRecorded (uint256 roundNum, address indexed node,
                                  uint256 kwhReduced, uint256 tokens);
    event RoundSettled           (uint256 roundNum, uint256 p2p, uint256 utility, uint256 unserved);
    event DataRevealed           (uint256 roundNum, address indexed node,
                                  uint256 produced, uint256 consumed);
    event BidRevealed            (uint256 roundNum, address indexed node, uint256 askPrice);
    event RevealVerified         (uint256 roundNum, address indexed node, bool valid);
    event AuditCIDStored         (uint256 roundNum, string cid);
    event PeakPricingSet         (uint256 roundNum, uint256 gridRate, bool isPeak);


    // CONSTRUCTOR & MODIFIERS


    constructor() {
        admin        = msg.sender;
        currentRound = 0;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }


    // NODE REGISTRATION


    function registerNode(
        address        _addr,
        string calldata _name,
        uint8          _role,
        uint8          _priority
    ) public onlyAdmin {
        require(!nodes[_addr].isRegistered, "Already registered");

        nodes[_addr] = Node({
            name:         _name,
            role:         Role(_role),
            priority:     Priority(_priority),
            isRegistered: true,
            rewardTokens: 0,
            creditBalance: 0
        });

        nodeAddresses.push(_addr);
        nodeCount++;
        emit NodeRegistered(_addr, _name, _role);
    }

    function setCommitteeSize(uint256 _size) public onlyAdmin {
        committeeSize = _size;
        emit CommitteeSizeSet(_size);
    }


    // ROUND MANAGEMENT


    function startRound(uint256 _utilityCapacity) public onlyAdmin {
        if (currentRound > 0) {
            require(rounds[currentRound].settled, "Previous round not settled");
        }
        currentRound++;
        rounds[currentRound].utilityCapacity = _utilityCapacity;
        emit RoundStarted(currentRound, _utilityCapacity);
    }


    // ENERGY COMMITMENT (privacy layer)


    function submitCommitment(bytes32 _commitHash) public {
        require(nodes[msg.sender].isRegistered, "Not registered");
        require(currentRound > 0,                "No active round");
        require(!rounds[currentRound].settled,   "Round already settled");
        require(!hasCommitted[currentRound][msg.sender], "Already committed");
        require(nodes[msg.sender].role != Role.UTILITY,  "Utility does not commit");

        commitments[currentRound][msg.sender]  = _commitHash;
        hasCommitted[currentRound][msg.sender] = true;
        roundCommitCount[currentRound]++;

        emit CommitmentSubmitted(currentRound, msg.sender);

        if (committeeSize > 0 && roundCommitCount[currentRound] >= committeeSize) {
            emit AllCommitted(currentRound);
        }
    }

    function submitCommitmentFor(address _node, bytes32 _commitHash) public onlyAdmin {
        require(nodes[_node].isRegistered, "Not registered");
        require(currentRound > 0, "No active round");
        require(!rounds[currentRound].settled, "Round settled");
        require(!hasCommitted[currentRound][_node], "Already committed");

        commitments[currentRound][_node]  = _commitHash;
        hasCommitted[currentRound][_node] = true;
        roundCommitCount[currentRound]++;

        emit CommitmentSubmitted(currentRound, _node);

        if (committeeSize > 0 && roundCommitCount[currentRound] >= committeeSize) {
            emit AllCommitted(currentRound);
        }
    }


    // FEED-IN BID COMMITMENT (auction fairness)


    function submitBidCommitment(bytes32 _bidHash) public {
        require(nodes[msg.sender].isRegistered, "Not registered");
        require(currentRound > 0, "No active round");
        require(!rounds[currentRound].settled, "Round settled");
        require(!hasBidCommitted[currentRound][msg.sender], "Already submitted bid");

        bidCommitments[currentRound][msg.sender]  = _bidHash;
        hasBidCommitted[currentRound][msg.sender] = true;

        emit BidCommitmentSubmitted(currentRound, msg.sender);
    }

    function submitBidCommitmentFor(address _node, bytes32 _bidHash) public onlyAdmin {
        require(nodes[_node].isRegistered, "Not registered");
        require(!hasBidCommitted[currentRound][_node], "Already submitted bid");

        bidCommitments[currentRound][_node]  = _bidHash;
        hasBidCommitted[currentRound][_node] = true;

        emit BidCommitmentSubmitted(currentRound, _node);
    }


    // MATCHING RESULTS — posted by admin after off-chain matching
    //
    // : Feed-in trades (type 2) are posted with pricePerKwh = 0.
    //     The actual price is SEALED until the seller reveals.
    //     Credits for sealed trades are recorded separately via
    //     recordSealedCredits() so the per-unit price is never
    //     visible on-chain until reveal.
    //
    //     Grid distribution trades (type 1) use the public grid
    //     rate (12c or 14c) — this is not sensitive information.


    function recordTrade(
        address _seller,
        address _buyer,
        uint256 _amount,
        uint256 _pricePerKwh,
        uint8   _tradeType
    ) public onlyAdmin {
        require(currentRound > 0, "No active round");
        require(!rounds[currentRound].settled, "Round settled");

        trades.push(Trade({
            seller:      _seller,
            buyer:       _buyer,
            amount:      _amount,
            pricePerKwh: _pricePerKwh,
            roundNum:    currentRound,
            tradeType:   _tradeType
        }));

        // For type 1 (grid distribution): buyer pays at public grid rate
        // For type 2 (feed-in, sealed): pricePerKwh is 0, credits via recordSealedCredits
        if (_pricePerKwh > 0) {
            nodes[_seller].creditBalance += int256(_amount * _pricePerKwh);
            nodes[_buyer].creditBalance  -= int256(_amount * _pricePerKwh);
        }

        if (_tradeType == 0) rounds[currentRound].totalP2PTraded      += _amount;
        if (_tradeType == 1) rounds[currentRound].totalUtilityTraded   += _amount;
        if (_tradeType == 2) rounds[currentRound].totalFeedIn          += _amount;
        rounds[currentRound].tradeCount++;

        emit TradeRecorded(currentRound, _seller, _buyer, _amount, _tradeType);
    }


    // SEALED CREDITS
    // Records credits for a feed-in seller without revealing the
    // per-unit price. The total credit amount is visible, but
    // without knowing the trade volume, observers cannot deduce
    // the exact ask price.
    //
    // After the seller reveals their bid, anyone can verify:
    //   revealedBidPrice * tradeAmount == credits earned


    function recordSealedCredits(
        address _node,
        int256  _credits
    ) public onlyAdmin {
        require(currentRound > 0, "No active round");

        nodes[_node].creditBalance += _credits;

        emit SealedCreditsRecorded(currentRound, _node, _credits);
    }


    // FULFILLMENT, DR, SETTLEMENT


    function recordFulfillment(
        address _node,
        uint256 _percentServed,
        bool    _isProducer
    ) public onlyAdmin {
        require(currentRound > 0, "No active round");

        fulfillments[currentRound][_node] = Fulfillment({
            percentServed: _percentServed,
            isProducer:    _isProducer,
            recorded:      true
        });

        emit FulfillmentRecorded(currentRound, _node, _percentServed);
    }

    function recordDemandResponse(address _node, uint256 _kwhReduced) public onlyAdmin {
        require(currentRound > 0, "No active round");

        uint256 tokens = _kwhReduced * DR_REWARD;
        nodes[_node].rewardTokens            += tokens;
        demandReductions[currentRound][_node] = _kwhReduced;
        rounds[currentRound].totalDRReduced  += _kwhReduced;

        emit DemandResponseRecorded(currentRound, _node, _kwhReduced, tokens);
    }

    function settleRound(uint256 _unserved) public onlyAdmin {
        require(currentRound > 0, "No active round");
        require(!rounds[currentRound].settled, "Already settled");

        if (committeeSize > 0) {
            require(
                roundCommitCount[currentRound] >= committeeSize,
                "Not all participants have submitted bids yet"
            );
        }

        rounds[currentRound].totalUnserved = _unserved;
        rounds[currentRound].settled       = true;

        emit RoundSettled(
            currentRound,
            rounds[currentRound].totalP2PTraded,
            rounds[currentRound].totalUtilityTraded,
            _unserved
        );
    }


    // IPFS AUDIT TRAIL ()
    // After settlement, admin pushes full round data to IPFS
    // and stores the CID on-chain. Permanent, decentralized audit.


    function setRoundAuditCID(uint256 _round, string calldata _cid) public onlyAdmin {
        require(rounds[_round].settled, "Round not settled yet");
        require(bytes(roundAuditCID[_round]).length == 0, "Audit CID already set");

        roundAuditCID[_round] = _cid;
        emit AuditCIDStored(_round, _cid);
    }


    // DYNAMIC PRICING ()
    // Records whether this round used peak pricing.


    function setRoundPricing(uint256 _round, bool _isPeak, uint256 _gridRate) public onlyAdmin {
        require(rounds[_round].settled, "Round not settled yet");

        isPeakRound[_round]  = _isPeak;
        roundGridRate[_round] = _gridRate;
        emit PeakPricingSet(_round, _gridRate, _isPeak);
    }


    // REVEAL — sellers prove their feed-in bid was honest
    //
    // After round settles, seller provides (askPrice, secret).
    // Contract verifies keccak256(askPrice, secret) == stored hash.
    // If valid, askPrice becomes public.
    //
    // Anyone can then verify:
    //   revealedBidPrice[round][seller] * tradeAmount == credits earned


    function revealBid(
        uint256       _round,
        uint256       _askPrice,
        string calldata _secret
    ) public {
        require(hasBidCommitted[_round][msg.sender], "No bid commitment for this round");
        require(rounds[_round].settled,              "Round not settled yet");
        require(!hasBidRevealed[_round][msg.sender], "Already revealed");

        bytes32 computed = keccak256(abi.encodePacked(_askPrice, _secret));
        require(
            computed == bidCommitments[_round][msg.sender],
            "Hash mismatch - bid data does not match commitment"
        );

        hasBidRevealed[_round][msg.sender]    = true;
        revealedBidPrice[_round][msg.sender]  = _askPrice;

        emit BidRevealed(_round, msg.sender, _askPrice);
    }

    // Dispute reveal for energy data
    function revealData(
        uint256       _round,
        uint256       _produced,
        uint256       _consumed,
        string calldata _secret
    ) public {
        require(hasCommitted[_round][msg.sender], "No commitment for this round");
        require(rounds[_round].settled, "Round not settled yet");

        bytes32 computed = keccak256(abi.encodePacked(_produced, _consumed, _secret));
        bool valid       = (computed == commitments[_round][msg.sender]);

        if (valid) {
            hasRevealed[_round][msg.sender]       = true;
            revealedProduced[_round][msg.sender]  = _produced;
            revealedConsumed[_round][msg.sender]  = _consumed;
            emit DataRevealed(_round, msg.sender, _produced, _consumed);
        }

        emit RevealVerified(_round, msg.sender, valid);
    }


    // CONVENIENCE


    function allCommitted() public view returns (bool) {
        if (committeeSize == 0 || currentRound == 0) return false;
        return roundCommitCount[currentRound] >= committeeSize;
    }

    function isRevealed(uint256 _round, address _node) public view returns (bool) {
        return hasRevealed[_round][_node];
    }


    // HASH HELPERS


    function generateCommitHash(
        uint256       _produced,
        uint256       _consumed,
        string calldata _secret
    ) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(_produced, _consumed, _secret));
    }

    function generateBidHash(
        uint256       _askPrice,
        string calldata _secret
    ) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(_askPrice, _secret));
    }


    // VIEW FUNCTIONS


    function getNodeInfo(address _addr) public view returns (
        string memory name, uint8 role, uint8 priority,
        uint256 tokens, int256 credits
    ) {
        Node storage n = nodes[_addr];
        return (n.name, uint8(n.role), uint8(n.priority), n.rewardTokens, n.creditBalance);
    }

    function getFulfillment(uint256 _round, address _node) public view returns (
        uint256 percentServed, bool isProducer, bool recorded
    ) {
        Fulfillment storage f = fulfillments[_round][_node];
        return (f.percentServed, f.isProducer, f.recorded);
    }

    function getRoundData(uint256 _round) public view returns (
        uint256 utilityCapacity, uint256 p2p, uint256 utility,
        uint256 feedin, uint256 drReduced, uint256 unserved,
        uint256 tradeCount, bool settled
    ) {
        RoundData storage rd = rounds[_round];
        return (rd.utilityCapacity, rd.totalP2PTraded, rd.totalUtilityTraded,
                rd.totalFeedIn, rd.totalDRReduced, rd.totalUnserved,
                rd.tradeCount, rd.settled);
    }

    function getTradeCount() public view returns (uint256) { return trades.length; }

    function getTrade(uint256 _index) public view returns (
        address seller, address buyer, uint256 amount,
        uint256 pricePerKwh, uint256 roundNum, uint8 tradeType
    ) {
        Trade storage t = trades[_index];
        return (t.seller, t.buyer, t.amount, t.pricePerKwh, t.roundNum, t.tradeType);
    }

    function getNodeAddress(uint256 _index) public view returns (address) {
        return nodeAddresses[_index];
    }

    function getCurrentRound() public view returns (uint256) { return currentRound; }
}
