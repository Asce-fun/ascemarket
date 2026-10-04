/* Run native Gnosis CTF 1.0.3 on an in-process local EVM. No live transactions.
 * Dependencies and exact install command: research/ctf/package.json.
 * ASCEMARKET_CTF_DEP_ROOT can point to an alternate dependency installation.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const root = path.resolve(process.env.ASCEMARKET_CTF_DEP_ROOT ||
  (fs.existsSync(path.join(__dirname,'node_modules','solc')) ? __dirname : '/private/tmp/ascemarket-ctf-evidence'));
const dep = name => require(require.resolve(name, {paths: [root]}));
const solc = dep('solc');
const {ethers} = dep('ethers');
const ganache = dep('ganache');
const U = 1000000n;
const Z = ethers.ZeroHash;
const tx = async promise => (await promise).wait();
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const input = {language:'Solidity', sources:{'EvidenceHelpers.sol':{content:fs.readFileSync(path.join(__dirname,'EvidenceHelpers.sol'),'utf8')}},
  settings:{optimizer:{enabled:true,runs:200},outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}};
const compiled = JSON.parse(solc.compile(JSON.stringify(input), p => {
  try { return {contents:fs.readFileSync(path.join(root,'node_modules',p),'utf8')}; }
  catch (e) { return {error:String(e)}; }
}));
const errors = (compiled.errors || []).filter(e => e.severity === 'error');
if (errors.length) throw Error(errors.map(e => e.formattedMessage).join('\n'));
const ctfFile = '@gnosis.pm/conditional-tokens-contracts/contracts/ConditionalTokens.sol';
const rpc = ganache.provider({logging:{quiet:true}, wallet:{deterministic:true,totalAccounts:8},
  chain:{hardfork:'shanghai',chainId:1337},miner:{blockGasLimit:30000000}});
// Snapshots change chain state without changing RPC arguments. Disable ethers'
// request cache so every assertion observes the restored branch's actual state.
const provider = new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1});
provider.pollingInterval = 10;
let signers, addresses, checks = 0, reverted = 0;
const equal = (a,b) => { assert.deepEqual(a,b); checks++; };
async function deploy(name,args=[],file='EvidenceHelpers.sol') {
  const a = compiled.contracts[file][name];
  const c = await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,signers[0]).deploy(...args);
  await c.waitForDeployment(); return c;
}
async function fixture(n,label) {
  const asset = await deploy('EvidenceToken');
  const ctf = await deploy('ConditionalTokens',[],ctfFile);
  const question = ethers.id(label);
  await tx(ctf.prepareCondition(addresses[0],question,n));
  const cid = await ctf.getConditionId(addresses[0],question,n);
  const aa = await asset.getAddress(), ca = await ctf.getAddress();
  const id = async mask => ctf.getPositionId(aa,await ctf.getCollectionId(Z,cid,mask));
  const bal = async (owner,mask) => ctf.balanceOf(addresses[owner],await id(mask));
  const cash = async owner => asset.balanceOf(addresses[owner]);
  const escrow = async () => asset.balanceOf(ca);
  const mint = async (owner,amount) => tx(asset.mint(addresses[owner],BigInt(amount)*U));
  const approve = async (owner,to) => tx(asset.connect(signers[owner]).approve(to,ethers.MaxUint256));
  const tokens = async (owner,to) => tx(ctf.connect(signers[owner]).setApprovalForAll(to,true));
  const split = async (owner,partition,amount=100) => {
    await approve(owner,ca); await tx(ctf.connect(signers[owner]).splitPosition(aa,Z,cid,partition,BigInt(amount)*U));
  };
  const merge = async (owner,partition,amount=100) => tx(ctf.connect(signers[owner]).mergePositions(aa,Z,cid,partition,BigInt(amount)*U));
  return {asset,ctf,question,cid,aa,ca,id,bal,cash,escrow,mint,approve,tokens,split,merge,n};
}
async function reject(promise) {
  let failed = false;
  try { await tx(promise); } catch(e) {
    if (e.code !== 'CALL_EXCEPTION') throw e;
    failed = true;
  }
  equal(failed,true); reverted++;
}
async function settleAll(f, holders, expectedBuyer) {
  const payouts = [];
  for (let outcome=0;outcome<f.n;outcome++) {
    const snapshot = await rpc.request({method:'evm_snapshot',params:[]});
    const before = await f.cash(2);
    const vector = Array.from({length:f.n},(_,i)=>i===outcome?1:0);
    await tx(f.ctf.reportPayouts(f.question,vector,{gasLimit:2000000}));
    for (const [owner,masks] of holders) {
      await tx(f.ctf.connect(signers[owner]).redeemPositions(f.aa,Z,f.cid,masks,{gasLimit:3000000}));
    }
    equal(await f.escrow(),0n);
    const paid = Number((await f.cash(2)-before)/U);
    equal(paid,expectedBuyer(outcome));
    payouts.push(paid);
    equal(await rpc.request({method:'evm_revert',params:[snapshot]}),true);
  }
  return payouts;
}
async function bookEvidence() {
  const f=await fixture(4,'common-outcomes-order-placement');
  await f.mint(1,100); await f.mint(2,30); await f.mint(3,40);
  await f.split(1,[1,2,4,8]);
  const book=await deploy('EvidenceBook',[f.aa,f.ca]), ba=await book.getAddress();
  await f.tokens(1,ba); await f.approve(2,ba); await f.approve(3,ba);
  for (const [mask,price] of [[1,30],[2,40],[1,30]])
    await tx(book.connect(signers[1]).post(await f.id(mask),100n*U,BigInt(price)*U));
  equal(await f.escrow(),100n*U); equal(await f.cash(1),0n);
  await tx(book.connect(signers[2]).fill(1,50n*U));
  equal((await book.orders(1)).filled,50n*U); equal(await f.cash(1),15n*U);
  await tx(book.connect(signers[2]).fill(1,50n*U));
  await tx(book.connect(signers[3]).fill(2,100n*U));
  equal(await f.escrow(),100n*U); equal(await f.cash(1),70n*U);
  // A second order could be posted against the same inventory. It is not reserved.
  await f.mint(4,30); await f.approve(4,ba);
  const buyerBefore=await f.cash(4),makerBefore=await f.cash(1);
  await reject(book.connect(signers[4]).fill(3,100n*U,{gasLimit:2000000}));
  equal(await f.cash(4),buyerBefore); equal(await f.cash(1),makerBefore);
  equal((await book.orders(3)).filled,0n);
  await tx(book.connect(signers[1]).cancel(3));
  await reject(book.connect(signers[4]).fill(3,100n*U,{gasLimit:2000000}));
  // Buy back half of A. Collateral cannot be merged without the missing B leg.
  await tx(f.asset.connect(signers[1]).transfer(addresses[2],15n*U));
  await tx(f.ctf.connect(signers[2]).safeTransferFrom(addresses[2],addresses[1],await f.id(1),50n*U,'0x'));
  await reject(f.ctf.connect(signers[1]).mergePositions(f.aa,Z,f.cid,[1,2,4,8],50n*U,{gasLimit:2000000}));
  equal(await f.escrow(),100n*U); equal(await f.bal(1,1),50n*U);
  await tx(f.asset.connect(signers[1]).transfer(addresses[3],20n*U));
  await tx(f.ctf.connect(signers[3]).safeTransferFrom(addresses[3],addresses[1],await f.id(2),50n*U,'0x'));
  await f.merge(1,[1,2,4,8],50);
  equal(await f.escrow(),50n*U); equal(await f.cash(1),85n*U);
  equal(await f.bal(1,4),50n*U); equal(await f.bal(1,8),50n*U);
  return {prefunded_maker_peak:100,order_placement_additional_collateral:0,
    after_sales_maker_net_contribution:30,partial_order_fills:2,
    stale_inventory_fill_reverted_without_payment:true,
    after_half_buyback_and_merge:{ctf_escrow:50,maker_wallet:85,maker_net_contribution:15}};
}
async function fundingEvidence() {
  const f=await fixture(4,'atomic-funded-common-condition');
  await f.mint(1,30); await f.mint(2,30); await f.mint(3,40);
  const router=await deploy('EvidenceFixedPurchase',[f.aa,f.ca,f.cid,addresses[1],addresses[2],addresses[3],false]);
  const ra=await router.getAddress();
  for(const owner of [1,2,3]) await f.approve(owner,ra);
  await tx(router.execute());
  equal(await f.escrow(),100n*U); equal(await f.cash(1),0n);
  equal(await f.bal(1,4),100n*U); equal(await f.bal(1,8),100n*U);
  await reject(router.execute({gasLimit:2000000}));
  const terminal=await settleAll(f,[[1,[4,8]],[2,[1]],[3,[2]]],i=>i===0?100:0);
  const seq=await fixture(4,'buyer-funded-sequential');
  await seq.mint(1,70); await seq.mint(2,30); await seq.mint(3,40);
  const first=await deploy('EvidenceFixedPurchase',[seq.aa,seq.ca,seq.cid,addresses[1],addresses[2],addresses[3],true]);
  const fa=await first.getAddress();
  await seq.approve(1,fa); await seq.approve(2,fa); await tx(first.execute());
  equal(await seq.escrow(),100n*U);
  await seq.split(1,[2,12]); // Partial split burns NO_A, requires no extra ERC20.
  equal(await seq.escrow(),100n*U); equal(await seq.cash(1),0n);
  await tx(seq.asset.connect(signers[3]).transfer(addresses[1],40n*U));
  await tx(seq.ctf.connect(signers[1]).safeTransferFrom(addresses[1],addresses[3],await seq.id(2),100n*U,'0x'));
  equal(await seq.cash(1),40n*U);
  // Separate binary conditions do not natively encode mutual exclusivity.
  const separate=await fixture(2,'independent-A');
  const qb=ethers.id('independent-B');
  await tx(separate.ctf.prepareCondition(addresses[0],qb,2));
  const cb=await separate.ctf.getConditionId(addresses[0],qb,2);
  await separate.mint(1,200); await separate.split(1,[1,2]);
  await tx(separate.ctf.connect(signers[1]).splitPosition(separate.aa,Z,cb,[1,2],100n*U));
  equal(await separate.escrow(),200n*U);
  await separate.mint(2,30); await separate.mint(3,40);
  await tx(separate.asset.connect(signers[2]).transfer(addresses[1],30n*U));
  await tx(separate.asset.connect(signers[3]).transfer(addresses[1],40n*U));
  await tx(separate.ctf.connect(signers[1]).safeTransferFrom(addresses[1],addresses[2],await separate.id(1),100n*U,'0x'));
  const binaryB=await separate.ctf.getPositionId(separate.aa,await separate.ctf.getCollectionId(Z,cb,1));
  await tx(separate.ctf.connect(signers[1]).safeTransferFrom(addresses[1],addresses[3],binaryB,100n*U,'0x'));
  equal(await separate.cash(1),70n*U);
  // Overlapping index sets are not a valid partition.
  const overlap=await fixture(4,'overlap-is-not-a-partition'); await overlap.mint(1,100); await overlap.approve(1,overlap.ca);
  await reject(overlap.ctf.connect(signers[1]).splitPosition(overlap.aa,Z,overlap.cid,[3,6],100n*U,{gasLimit:2000000}));
  equal(await overlap.escrow(),0n); equal(await overlap.cash(1),100n*U);
  return {common_condition:{atomic_maker_peak:30,total_ctf_backing:100,terminal_buyer_A_payouts:terminal,
    sequential_maker_peak:70,sequential_final_net_contribution:30},
    separate_binary_conditions:{total_ctf_backing:200,net_contribution_after_70_premiums:130},
    overlapping_partition_rejected:true};
}
async function exceptionEvidence() {
  // Native CTF baskets reproduce unequal state payouts, although this is a
  // multi-token holding per customer, not one transferable custom-cover token.
  const f=await fixture(4,'refunds-are-part-of-collateral');
  await f.mint(1,120); await f.split(1,[1,2,4,8],120);
  await f.mint(2,30); await f.mint(3,40);
  for(const [owner,normalMask,premium] of [[2,1,30],[3,2,40]]) {
    await tx(f.asset.connect(signers[owner]).transfer(addresses[1],BigInt(premium)*U));
    await tx(f.ctf.connect(signers[1]).safeTransferFrom(addresses[1],addresses[owner],await f.id(normalMask),100n*U,'0x'));
    await tx(f.ctf.connect(signers[1]).safeTransferFrom(addresses[1],addresses[owner],await f.id(8),60n*U,'0x'));
  }
  equal(await f.escrow(),120n*U); equal(await f.cash(1),70n*U);
  const buyerA=await settleAll(f,[[1,[1,2,4]],[2,[1,8]],[3,[2,8]]],i=>i===0?100:i===3?60:0);
  return {per_cover_normal_cap:100,per_cover_cancellation_payout:60,
    common_condition_backing:120,maker_net_contribution_after_70_premiums:50,
    buyer_A_payouts:buyerA,customer_representation:'Two CTF positions per cover; a single custom token would require a custody wrapper.'};
}
async function intervalFixture(label,sourceBidFunds=15) {
  const f=await fixture(9,label);
  await f.mint(1,100); await f.split(1,[252,259]);
  await f.mint(4,100); await f.split(4,[254,257]);
  await f.mint(3,sourceBidFunds); await f.mint(2,37);
  const route=await deploy('EvidenceIntervalRoute',[f.aa,f.ca,f.cid,addresses[2],addresses[1],addresses[3],addresses[4]]);
  const ra=await route.getAddress();
  for(const owner of [1,2,3,4]) { await f.approve(owner,ra); await f.tokens(owner,ra); }
  return {...f,route};
}
async function intervalEvidence() {
  const f=await intervalFixture('new-interval-from-related-liquidity');
  await tx(f.route.connect(signers[2]).buy());
  equal(await f.bal(2,28),100n*U); equal(await f.bal(3,224),100n*U);
  equal(await f.escrow(),200n*U); equal(await f.route.stage(),1n);
  const buyPayouts=await settleAll(f,[[1,[259]],[4,[254,257]],[3,[224]],[2,[28]]],i=>i>=2&&i<5?100:0);
  await tx(f.route.connect(signers[2]).change());
  equal(await f.bal(2,28),0n); equal(await f.bal(2,30),100n*U);
  const changePayouts=await settleAll(f,[[1,[252,259]],[4,[257]],[3,[224]],[2,[30]]],i=>i>=1&&i<5?100:0);
  await f.merge(1,[252,259]); equal(await f.escrow(),100n*U);
  await tx(f.route.connect(signers[2]).close());
  equal(await f.bal(2,30),0n); equal(await f.cash(2),32n*U);
  await f.merge(4,[254,257]); equal(await f.escrow(),0n);
  const finalWallets = {};
  for (const owner of [1,2,3,4]) finalWallets[owner]=Number(await f.cash(owner)/U);
  equal(finalWallets,{'1':102,'2':32,'3':16,'4':102});
  for (const owner of [1,2,3,4]) for (const mask of [2,28,30,224,252,254,257,259]) equal(await f.bal(owner,mask),0n);
  const fail=await intervalFixture('underfunded-source-bid',0);
  const before=[await fail.cash(2),await fail.cash(1),await fail.bal(1,252),await fail.escrow()];
  await reject(fail.route.connect(signers[2]).buy({gasLimit:3000000}));
  equal([await fail.cash(2),await fail.cash(1),await fail.bal(1,252),await fail.escrow()],before);
  equal(await fail.route.stage(),0n);
  const expired=await intervalFixture('expired-route');
  await rpc.request({method:'evm_increaseTime',params:[3601]}); await rpc.request({method:'evm_mine',params:[]});
  await reject(expired.route.connect(signers[2]).buy({gasLimit:3000000}));
  equal(await expired.route.stage(),0n);
  return {direct_interval_orderbook_present:false,states:'0..7 plus cancellation',
    buy:{cover:'[2,5)',source_ask_T2:40,source_bid_T5:15,buyer_price:25,terminal_payouts:buyPayouts},
    change:{cover:'[1,5)',source_ask_T1:50,source_bid_T2:38,buyer_increment:12,terminal_payouts:changePayouts},
    close:{source_bid_T1:48,source_ask_T5:16,buyer_proceeds:32},
    final_wallets:finalWallets,final_ctf_escrow:0,buyer_roundtrip_loss_without_fees:5,
    source_maker_roundtrip_gross_profits:[2,1,2],
    underfunded_source_bid_reverted_all_legs:true,expiry_enforced:true};
}
(async()=>{
  signers=await Promise.all(Array.from({length:8},(_,i)=>provider.getSigner(i)));
  addresses=await Promise.all(signers.map(s=>s.getAddress()));
  const orderbook=await bookEvidence(); console.log('Order placement, fills, stale inventory, partial buyback: passed');
  const funding=await fundingEvidence(); console.log('Atomic/sequential funding, independent conditions, terminal redemptions: passed');
  const exceptions=await exceptionEvidence(); console.log('Nonzero cancellation refunds and unequal payout baskets: passed');
  const marketplace=await intervalEvidence(); console.log('Native CTF interval buy/change/close and all terminal outcomes: passed');
  const result={scope:'Local EVM research, synthetic quotes, fixed test-only execution adapters; no production exchange or demand validation.',
    date:'2026-09-30',compiler:solc.version(),ctf_package:'@gnosis.pm/conditional-tokens-contracts@1.0.3',
    ganache_version:dep('ganache/package.json').version,ethers_version:ethers.version,
    source_sha256:{upstream_ctf:hash(path.join(root,'node_modules',ctfFile)),helpers:hash(path.join(__dirname,'EvidenceHelpers.sol')),runner:hash(__filename)},
    assertion_count:checks,expected_reverted_transactions:reverted,terminal_redemption_scenarios:26,
    orderbook,funding,exceptions,marketplace};
  fs.writeFileSync(path.join(__dirname,'ctf-evidence-results.json'),JSON.stringify(result,null,2)+'\n');
  console.log(`Passed ${checks} assertions; ${reverted} expected transaction reverts; 26 terminal scenarios.`);
  await provider.destroy(); await rpc.disconnect();
})().catch(async e=>{console.error(e); await rpc.disconnect(); process.exitCode=1;});
