function makePack(overrides = {}) {
  const packId = overrides.packId || 'pack-default';
  return {
    metadata: {
      pack_id: packId,
      pack_name: overrides.packName || `Pack ${packId}`,
      version: overrides.version || '1.0.0',
      description: overrides.description || 'Mock pack for Playwright runtime tests',
      category: overrides.category || 'test',
    },
    workflow: overrides.workflow || { steps: [] },
  };
}

function buildDefaultState(options = {}) {
  const packs = options.packs || [makePack({ packId: 'pack-1', packName: 'Alpha Pack' }), makePack({ packId: 'pack-2', packName: 'Beta Pack' })];
  return {
    packs,
    activePack: options.activePack || null,
    optionsPageOpened: false,
    runtimeMessages: [],
    tabMessages: [],
    lastLoadedPackId: null,
    tabStatus: options.tabStatus || {
      status: 'idle',
      currentStepIndex: 0,
      totalSteps: 0,
    },
  };
}

async function installChromeHostMock(page, options = {}) {
  await page.addInitScript((rawOptions) => {
    const options = rawOptions || {};

    const state = {
      ...options.initialState,
      runtimeMessages: [],
      tabMessages: [],
      optionsPageOpened: false,
      lastLoadedPackId: null,
      packs: Array.isArray(options.initialState?.packs) ? options.initialState.packs : [],
      activePack: options.initialState?.activePack || null,
      tabStatus: options.initialState?.tabStatus || {
        status: 'idle',
        currentStepIndex: 0,
        totalSteps: 0,
      },
    };

    const runtimeBehavior = options.runtimeBehavior || {};
    const mockOptions = options.mockOptions || {};
    const timeoutActions = Array.isArray(mockOptions.tabsSendMessageTimeoutActions)
      ? mockOptions.tabsSendMessageTimeoutActions
      : ['executePack'];
    const failureActions = Array.isArray(mockOptions.tabsSendMessageFailsActions)
      ? mockOptions.tabsSendMessageFailsActions
      : ['executePack'];

    function ok(data) {
      return { ok: true, data };
    }

    function fail(message, code = 'MOCK_ERROR') {
      return {
        ok: false,
        code,
        error: {
          code,
          message,
        },
      };
    }

    const storageLocal = {
      async get(keys) {
        // 模拟 storage.get 失败
        if (mockOptions.storageGetFails) {
          throw new Error('Storage get failed');
        }

        if (!keys) {
          return { activePack: state.activePack };
        }

        if (Array.isArray(keys) && keys.includes('activePack')) {
          return { activePack: state.activePack };
        }

        if (typeof keys === 'string' && keys === 'activePack') {
          return { activePack: state.activePack };
        }

        if (typeof keys === 'object' && Object.prototype.hasOwnProperty.call(keys, 'activePack')) {
          return { activePack: state.activePack ?? keys.activePack };
        }

        return {};
      },

      async set(items) {
        if (items && Object.prototype.hasOwnProperty.call(items, 'activePack')) {
          state.activePack = items.activePack;
        }
      },
    };

    const runtime = {
      async sendMessage(message) {
        state.runtimeMessages.push(message);

        if (runtimeBehavior.forceFailure) {
          return fail(runtimeBehavior.forceFailure);
        }

        switch (message.action) {
          case 'listPacks':
            return ok(state.packs);

          case 'loadPack': {
            const pack = state.packs.find((item) => item.metadata.pack_id === message?.data?.packId);
            if (!pack) {
              return fail(`Pack not found: ${message?.data?.packId}`, 'PACK_NOT_FOUND');
            }
            state.lastLoadedPackId = pack.metadata.pack_id;
            state.activePack = pack;
            return ok(pack);
          }

          case 'deletePack': {
            const packId = message?.data?.packId;
            state.packs = state.packs.filter((item) => item.metadata.pack_id !== packId);
            if (state.activePack?.metadata?.pack_id === packId) {
              state.activePack = null;
            }
            return ok({ deleted: true, packId });
          }

          case 'savePack': {
            const pack = message?.data?.pack;
            if (!pack?.metadata?.pack_id) {
              return fail('Invalid pack payload', 'INVALID_PACK');
            }
            state.packs.push(pack);
            return ok(pack);
          }

          default:
            return ok(null);
        }
      },

      async openOptionsPage() {
        state.optionsPageOpened = true;
      },
    };

    const tabs = {
      async query() {
        return [{ id: 9001, url: 'https://example.com' }];
      },

      async sendMessage(tabId, payload) {
        const action = payload?.action;
        state.tabMessages.push({ tabId, payload });

        // 模拟 tabs.sendMessage 失败
        if (mockOptions.tabsSendMessageFails && failureActions.includes(action)) {
          throw new Error('Tabs send message failed');
        }

        // 模拟超时
        if (mockOptions.tabsSendMessageTimeout && timeoutActions.includes(action)) {
          return new Promise(() => {
            setTimeout(() => {}, Number(mockOptions.tabsSendMessageTimeout) || 5000);
          });
        }

        switch (action) {
          case 'getStatus':
            return ok(state.tabStatus);
          case 'executePack':
            state.tabStatus = {
              status: 'completed',
              currentStepIndex: 1,
              totalSteps: 1,
            };
            return ok({ completed: true });
          case 'pause':
            state.tabStatus = { ...state.tabStatus, status: 'paused' };
            return ok(state.tabStatus);
          case 'resume':
            state.tabStatus = { ...state.tabStatus, status: 'running' };
            return ok(state.tabStatus);
          case 'stop':
            state.tabStatus = {
              status: 'idle',
              currentStepIndex: 0,
              totalSteps: 0,
            };
            return ok(state.tabStatus);
          case 'loadPack':
            return ok({ loaded: true });
          default:
            return ok(null);
        }
      },
    };

    globalThis.chrome = {
      storage: { local: storageLocal },
      runtime,
      tabs,
    };

    globalThis.__chromeMockState = state;

    globalThis.confirm = () => true;
  }, {
    initialState: buildDefaultState(options),
    runtimeBehavior: options.runtimeBehavior || {},
    mockOptions: options.mockOptions || {},
  });
}

module.exports = {
  makePack,
  buildDefaultState,
  installChromeHostMock,
};
