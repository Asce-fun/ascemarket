/* Test the new arbitrary-vector examples with the existing published CTF.
 * No new Solidity; no live chain. Prefunded inventory, separate transfers,
 * synthetic premiums. Not a production atomic executor or an authorization test.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const depRoot = path.resolve(process.env.ASCEMARKET_CTF_DEP_ROOT ||
  (fs.existsSync(path.join(__dirname, 'node_modules/solc')) ? __dirname : '/private/tmp/ascemarket-ctf-evidence'));
const dep = name => require(require.resolve(name, {paths: [depRoot]}));
const solc = dep('solc');
const ganache = dep('ganache');
const {ethers} = dep('ethers');
const U = 1000000n;
const covers = [[10000,6000,2000,0,0,0], [0,0,2000,7000,10000,0], [1000,5000,6000,4000,0,0]];
const premiums = [2300,2600,2100];
const total = covers[0].map((_,k)=>covers.reduce((s,f)=>s+f[k],0));
const M = Math.max(...total);
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const input = {language:'Solidity', sources:{'EvidenceHelpers.sol':{content:fs.readFileSync(path.join(__dirname,'EvidenceHelpers.sol'),'utf8')}},
  settings:{optimizer:{enabled:true,runs:200},outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}};
const compiled = JSON.parse(solc.compile(JSON.stringify(input), p=>{
  try {return {contents:fs.readFileSync(path.join(depRoot,'node_modules',p),'utf8')};}
  catch(e) {return {error:String(e)};}
}));
const errors = (compiled.errors||[]).filter(e=>e.severity==='error');
if(errors.length) throw Error(errors.map(e=>e.formattedMessage).join('\n'));
const ctfFile = '@gnosis.pm/conditional-tokens-contracts/contracts/ConditionalTokens.sol';
const rpc = ganache.provider({logging:{quiet:true},wallet:{deterministic:true,totalAccounts:5},
  chain:{hardfork:'shanghai',chainId:1337},miner:{blockGasLimit:30000000}});
const provider = new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1});
provider.pollingInterval = 10;
let checks = 0;
const eq = (a,b)=>{assert.deepEqual(a,b); checks++;};
const tx = async promise=>(await promise).wait();
(async()=>{
  const signers = await Promise.all(Array.from({length:5},(_,i)=>provider.getSigner(i)));
  const addresses = await Promise.all(signers.map(s=>s.getAddress()));
  const deploy = async(name,file='EvidenceHelpers.sol')=>{
    const artifact = compiled.contracts[file][name];
    const c = await new ethers.ContractFactory(artifact.abi,artifact.evm.bytecode.object,signers[0]).deploy();
    await c.waitForDeployment(); return c;
  };
  const token = await deploy('EvidenceToken');
  const ctf = await deploy('ConditionalTokens',ctfFile);
  const ta = await token.getAddress(), ca = await ctf.getAddress();
  const question = ethers.id('single-event-arbitrary-vector-baseline-2026-09-30');
  await tx(ctf.prepareCondition(addresses[0],question,6));
  const condition = await ctf.getConditionId(addresses[0],question,6);
  const masks = Array.from({length:6},(_,k)=>1<<k);
  const ids = await Promise.all(masks.map(async m=>ctf.getPositionId(ta,await ctf.getCollectionId(ethers.ZeroHash,condition,m))));
  await tx(token.mint(addresses[1],BigInt(M)*U));
  await tx(token.connect(signers[1]).approve(ca,BigInt(M)*U));
  const split = await tx(ctf.connect(signers[1]).splitPosition(ta,ethers.ZeroHash,condition,masks,BigInt(M)*U));
  const deliveryGas=[];
  for(let j=0;j<3;j++){
    await tx(token.mint(addresses[j+2],BigInt(premiums[j])*U));
    await tx(token.connect(signers[j+2]).transfer(addresses[1],BigInt(premiums[j])*U));
    const ks = masks.map((_,k)=>k).filter(k=>covers[j][k]>0);
    const receipt = await tx(ctf.connect(signers[1]).safeBatchTransferFrom(addresses[1],addresses[j+2],
      ks.map(k=>ids[k]),ks.map(k=>BigInt(covers[j][k])*U),'0x'));
    deliveryGas.push(Number(receipt.gasUsed));
    for(let k=0;k<6;k++) eq(await ctf.balanceOf(addresses[j+2],ids[k]),BigInt(covers[j][k])*U);
  }
  eq(await token.balanceOf(ca),BigInt(M)*U);
  for(let k=0;k<6;k++) eq(await ctf.balanceOf(addresses[1],ids[k]),BigInt(M-total[k])*U);
  const branches = async(label,currentCovers,backing)=>{
    const rows=[];
    for(let k=0;k<6;k++){
      const snapshot = await rpc.request({method:'evm_snapshot',params:[]});
      const before = await Promise.all(addresses.slice(1).map(a=>token.balanceOf(a)));
      const report = await tx(ctf.reportPayouts(question,masks.map((_,s)=>s===k?1:0)));
      const redemptionGas=[];
      for(let holder=1;holder<5;holder++){
        const receipt = await tx(ctf.connect(signers[holder]).redeemPositions(ta,ethers.ZeroHash,condition,masks));
        redemptionGas.push(Number(receipt.gasUsed));
      }
      const after = await Promise.all(addresses.slice(1).map(a=>token.balanceOf(a)));
      const paid = after.map((v,i)=>Number((v-before[i])/U));
      const buyers = currentCovers.map(f=>f[k]);
      eq(paid,[backing-buyers.reduce((a,b)=>a+b,0),...buyers]);
      eq(await token.balanceOf(ca),0n);
      rows.push({state:k,payout_usdc:paid,report_gas:Number(report.gasUsed),redemption_gas:redemptionGas});
      eq(await rpc.request({method:'evm_revert',params:[snapshot]}),true);
    }
    return {label,rows};
  };
  const opened = await branches('A',covers,M);
  const ck = covers[2].map((_,k)=>k).filter(k=>covers[2][k]>0);
  await tx(token.connect(signers[1]).transfer(addresses[4],400n*U));
  const buyback = await tx(ctf.connect(signers[4]).safeBatchTransferFrom(addresses[4],addresses[1],
    ck.map(k=>ids[k]),ck.map(k=>BigInt(covers[2][k]/2)*U),'0x'));
  const merge = await tx(ctf.connect(signers[1]).mergePositions(ta,ethers.ZeroHash,condition,masks,500n*U));
  eq(await token.balanceOf(ca),10500n*U);
  eq(await token.balanceOf(addresses[1]),7100n*U); // 7000 premium -400 buyback +500 merge
  const closedCovers = [covers[0],covers[1],covers[2].map(v=>v/2)];
  const closed = await branches('C',closedCovers,10500);
  const result = {date:'2026-09-30',scope:'Local CTF mechanics; prefunded inventory; separate unsigned-harness transfers; synthetic premiums.',
    ctf_package:'@gnosis.pm/conditional-tokens-contracts@1.0.3',compiler:solc.version(),
    ganache:dep('ganache/package.json').version,hardfork:'shanghai',
    assertions:checks,terminal_redemption_scenarios:12,
    example_A:{covers_usdc:covers,aggregate_usdc:total,naive_backing_usdc:26000,ctf_backing_usdc:M},
    example_C:{backing_usdc:10500,backing_released_usdc:500,buyback_usdc:400,net_cash_release_usdc:100},
    gas:{full_six_state_split:Number(split.gasUsed),buyer_batch_deliveries:deliveryGas,
         half_C_batch_buyback:Number(buyback.gasUsed),full_set_500_merge:Number(merge.gasUsed)},
    settlement:[opened,closed],source_sha256:{runner:hash(__filename),helpers:hash(path.join(__dirname,'EvidenceHelpers.sol')),
      ctf:hash(path.join(depRoot,'node_modules',ctfFile))}};
  fs.writeFileSync(path.join(__dirname,'state-clearing-baseline-results.json'),JSON.stringify(result,null,2)+'\n');
  console.log(`Shared CTF condition: 26,000 -> ${M} backing; half-C releases 500; net release 100.`);
  console.log(`Passed ${checks} assertions and 12 redemption scenarios. Gas: ${JSON.stringify(result.gas)}`);
  await provider.destroy(); await rpc.disconnect();
})().catch(async e=>{console.error(e); await rpc.disconnect(); process.exitCode=1;});
