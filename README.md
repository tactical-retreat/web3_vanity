# web3_vanity

This repo contains two very lazy scripts that calcualte vanity addresses. There might be others that are better. I just used Claude to create most of it and tweaked what I needed.

I used it to generate the vanity address for $ket. It took less than 10 minutes, did something like 500K checks per second on my PC.

There's one script that checks for the 0 nonce (contract deployed at first tx). The advantage of this is that it's argument/bytecode independent, the disadvantage is that you have to make sure the nonce matches. So for example, deploy as the first tx on every chain.

That's easy to mess up though, so there's and another which can be used along with the CREATE2 factory. You need to provide the hash of the bytecode and the arguments to the contract for that one. I ended up not using that version (even though I preferred it) because it seems like I need to deploy the contract with different arguments on every chain for Layer Zero support. If you don't have that restriction, this is probably better. 
