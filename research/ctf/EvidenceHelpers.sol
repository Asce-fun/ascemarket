pragma solidity ^0.5.17;

import "@gnosis.pm/conditional-tokens-contracts/contracts/ConditionalTokens.sol";
import "openzeppelin-solidity/contracts/token/ERC20/ERC20.sol";

// Research fixtures only. These fixed transactions are not a production exchange.
contract EvidenceToken is ERC20 {
    function mint(address owner, uint256 amount) external { _mint(owner, amount); }
}

contract EvidenceReceiver {
    function onERC1155Received(address, address, uint256, uint256, bytes calldata)
        external returns (bytes4) { return 0xf23a6e61; }
    function onERC1155BatchReceived(address, address, uint256[] calldata, uint256[] calldata, bytes calldata)
        external returns (bytes4) { return 0xbc197c81; }
}

contract EvidenceBook {
    struct Order { address seller; uint256 id; uint256 amount; uint256 payment; uint256 filled; bool cancelled; }
    EvidenceToken public asset;
    ConditionalTokens public ctf;
    uint256 public sequence;
    mapping(uint256 => Order) public orders;
    constructor(EvidenceToken a, ConditionalTokens c) public { asset = a; ctf = c; }
    function post(uint256 id, uint256 amount, uint256 payment) external returns (uint256) {
        require(amount > 0 && ctf.balanceOf(msg.sender, id) >= amount, "missing inventory");
        require(ctf.isApprovedForAll(msg.sender, address(this)), "missing token approval");
        sequence++;
        orders[sequence] = Order(msg.sender, id, amount, payment, 0, false);
        // No collateral transfer and no CTF mint on placement.
        return sequence;
    }
    function cancel(uint256 orderId) external {
        require(orders[orderId].seller == msg.sender, "not owner");
        orders[orderId].cancelled = true;
    }
    function fill(uint256 orderId, uint256 amount) external {
        Order storage o = orders[orderId];
        require(o.seller != address(0) && !o.cancelled && amount > 0, "inactive order");
        require(o.filled + amount <= o.amount, "overfill");
        require((o.payment * amount) % o.amount == 0, "inexact fill");
        o.filled += amount;
        require(asset.transferFrom(msg.sender, o.seller, o.payment * amount / o.amount), "payment failed");
        ctf.safeTransferFrom(o.seller, msg.sender, o.id, amount, "");
    }
}

contract EvidenceFixedPurchase is EvidenceReceiver {
    EvidenceToken public asset;
    ConditionalTokens public ctf;
    bytes32 public condition;
    address public maker;
    address public buyerA;
    address public buyerB;
    bool public firstOnly;
    bool public executed;
    uint256 constant UNIT = 1000000;
    constructor(EvidenceToken a, ConditionalTokens c, bytes32 conditionId,
                address m, address ba, address bb, bool onlyA) public {
        asset = a; ctf = c; condition = conditionId;
        maker = m; buyerA = ba; buyerB = bb; firstOnly = onlyA;
        asset.approve(address(ctf), uint256(-1));
    }
    function id(uint256 mask) public view returns (uint256) {
        return ctf.getPositionId(asset, ctf.getCollectionId(bytes32(0), condition, mask));
    }
    function execute() external {
        require(!executed, "used");
        executed = true;
        require(asset.transferFrom(maker, address(this), (firstOnly ? 70 : 30) * UNIT), "maker funds");
        require(asset.transferFrom(buyerA, address(this), 30 * UNIT), "A funds");
        if (!firstOnly) require(asset.transferFrom(buyerB, address(this), 40 * UNIT), "B funds");
        uint256[] memory partition = new uint256[](firstOnly ? 2 : 4);
        partition[0] = 1;
        if (firstOnly) partition[1] = 14;
        else { partition[1] = 2; partition[2] = 4; partition[3] = 8; }
        ctf.splitPosition(asset, bytes32(0), condition, partition, 100 * UNIT);
        ctf.safeTransferFrom(address(this), buyerA, id(1), 100 * UNIT, "");
        if (firstOnly) ctf.safeTransferFrom(address(this), maker, id(14), 100 * UNIT, "");
        else {
            ctf.safeTransferFrom(address(this), buyerB, id(2), 100 * UNIT, "");
            ctf.safeTransferFrom(address(this), maker, id(4), 100 * UNIT, "");
            ctf.safeTransferFrom(address(this), maker, id(8), 100 * UNIT, "");
        }
    }
}

// A fixed, buyer-triggered route over nine outcomes (values 0..7, cancellation).
// Masks: T2=252, T5=224, C=[2,5)=28, T1=254, E=[1,2)=2, D=[1,5)=30.
// All recipients, consideration and quantities are fixed at deployment.
contract EvidenceIntervalRoute is EvidenceReceiver {
    EvidenceToken public asset;
    ConditionalTokens public ctf;
    bytes32 public condition;
    address public buyer;
    address public makerT2;
    address public makerT5;
    address public makerT1;
    uint256 public stage;
    uint256 public expiry;
    uint256 constant UNIT = 1000000;
    constructor(EvidenceToken a, ConditionalTokens c, bytes32 conditionId,
                address u, address m2, address m5, address m1) public {
        asset = a; ctf = c; condition = conditionId;
        buyer = u; makerT2 = m2; makerT5 = m5; makerT1 = m1;
        expiry = block.timestamp + 3600;
    }
    function id(uint256 mask) public view returns (uint256) {
        return ctf.getPositionId(asset, ctf.getCollectionId(bytes32(0), condition, mask));
    }
    function check(uint256 expectedStage) internal view {
        require(msg.sender == buyer && stage == expectedStage, "wrong caller/stage");
        require(block.timestamp < expiry && ctf.payoutDenominator(condition) == 0, "closed");
    }
    function pair(uint256 a, uint256 b) internal pure returns (uint256[] memory p) {
        p = new uint256[](2); p[0] = a; p[1] = b;
    }
    function buy() external {
        check(0); stage = 1;
        require(asset.transferFrom(buyer, makerT2, 25 * UNIT), "buyer payment");
        require(asset.transferFrom(makerT5, makerT2, 15 * UNIT), "T5 payment");
        ctf.safeTransferFrom(makerT2, address(this), id(252), 100 * UNIT, "");
        ctf.splitPosition(asset, bytes32(0), condition, pair(28, 224), 100 * UNIT);
        ctf.safeTransferFrom(address(this), buyer, id(28), 100 * UNIT, "");
        ctf.safeTransferFrom(address(this), makerT5, id(224), 100 * UNIT, "");
    }
    function change() external {
        check(1); stage = 2;
        require(asset.transferFrom(buyer, makerT1, 12 * UNIT), "buyer payment");
        require(asset.transferFrom(makerT2, makerT1, 38 * UNIT), "T2 payment");
        ctf.safeTransferFrom(buyer, address(this), id(28), 100 * UNIT, "");
        ctf.safeTransferFrom(makerT1, address(this), id(254), 100 * UNIT, "");
        ctf.splitPosition(asset, bytes32(0), condition, pair(2, 252), 100 * UNIT);
        ctf.safeTransferFrom(address(this), makerT2, id(252), 100 * UNIT, "");
        ctf.mergePositions(asset, bytes32(0), condition, pair(2, 28), 100 * UNIT);
        ctf.safeTransferFrom(address(this), buyer, id(30), 100 * UNIT, "");
    }
    function close() external {
        check(2); stage = 3;
        require(asset.transferFrom(makerT1, buyer, 32 * UNIT), "buyer proceeds");
        require(asset.transferFrom(makerT1, makerT5, 16 * UNIT), "T5 payment");
        ctf.safeTransferFrom(buyer, address(this), id(30), 100 * UNIT, "");
        ctf.safeTransferFrom(makerT5, address(this), id(224), 100 * UNIT, "");
        ctf.mergePositions(asset, bytes32(0), condition, pair(30, 224), 100 * UNIT);
        ctf.safeTransferFrom(address(this), makerT1, id(254), 100 * UNIT, "");
    }
}
