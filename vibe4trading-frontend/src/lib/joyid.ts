import { initConfig } from '@joyid/evm';

export function initJoyID() {
  initConfig({
    name: 'Vibe4Trading',
    logo: '/v4t_transparent_1600.png',
    joyidAppURL: 'https://app.joy.id',
    network: {
      chainId: 1,
      name: 'Ethereum Mainnet',
    },
  });
}

export function getJoyIDConfig() {
  return {
    name: 'Vibe4Trading',
    logo: '/v4t_transparent_1600.png',
    joyidAppURL: 'https://app.joy.id',
    network: {
      chainId: 1,
      name: 'Ethereum Mainnet',
    },
  };
}
