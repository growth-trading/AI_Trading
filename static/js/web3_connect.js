/* AITrading — MetaMask / Web3 Connection */

const BSC_CHAIN_ID = '0x38'; // BSC Mainnet = 56 dec

async function connectMetaMask() {
  if (typeof window.ethereum === 'undefined') {
    showToast('MetaMask chưa được cài đặt. Vui lòng cài MetaMask để tiếp tục.', 'error');
    window.open('https://metamask.io/download/', '_blank');
    return;
  }

  try {
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    if (!accounts.length) return;

    await switchToBSC();
    displayWallet(accounts[0]);
  } catch (err) {
    if (err.code === 4001) {
      showToast('Kết nối MetaMask bị từ chối.', 'error');
    } else {
      showToast('Lỗi kết nối MetaMask: ' + err.message, 'error');
    }
  }
}

async function switchToBSC() {
  try {
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: BSC_CHAIN_ID }],
    });
  } catch (err) {
    if (err.code === 4902) {
      await window.ethereum.request({
        method: 'wallet_addEthereumChain',
        params: [{
          chainId: BSC_CHAIN_ID,
          chainName: 'BNB Smart Chain',
          nativeCurrency: { name: 'BNB', symbol: 'BNB', decimals: 18 },
          rpcUrls: ['https://bsc-dataseed.binance.org/'],
          blockExplorerUrls: ['https://bscscan.com'],
        }],
      });
    }
  }
}

function displayWallet(address) {
  const btn = document.getElementById('connectWalletBtn');
  const addrDiv = document.getElementById('walletAddress');
  if (btn) {
    btn.innerHTML = `<i class="bi bi-check-circle-fill me-2 text-success"></i>Đã kết nối`;
    btn.disabled = true;
  }
  if (addrDiv) {
    const short = address.slice(0, 6) + '...' + address.slice(-4);
    addrDiv.textContent = `Ví: ${short}`;
    addrDiv.classList.remove('d-none');
  }
  showToast(`Đã kết nối ví ${address.slice(0, 6)}...${address.slice(-4)}`, 'success');
}

// Auto-reconnect if already connected
window.addEventListener('load', async () => {
  if (typeof window.ethereum !== 'undefined') {
    try {
      const accounts = await window.ethereum.request({ method: 'eth_accounts' });
      if (accounts.length) displayWallet(accounts[0]);
    } catch (_) {}

    window.ethereum.on('accountsChanged', (accounts) => {
      if (accounts.length) displayWallet(accounts[0]);
      else location.reload();
    });
  }
});
