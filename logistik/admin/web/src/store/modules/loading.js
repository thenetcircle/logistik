import * as actions from '@/store/actions';
import * as mutations from '@/store/mutations';

const moduleState = {
  isGlobalLoadingShowing: false,
  isLoadingMuskShowing: false,
};

const moduleGetters = {
  isGlobalLoadingShowing(state) {
    return state.isGlobalLoadingShowing;
  },
  isLoadingMuskShowing(state) {
    return state.isLoadingMuskShowing;
  },
};

const moduleMutations = {
  [mutations.UPDATE_GLOBAL_LOADING_STATUS](state, { status, withMusk }) {
    state.isGlobalLoadingShowing = status;
    state.isLoadingMuskShowing = withMusk || false;
  },
};

const moduleActions = {
  [actions.SHOW_GLOBAL_LOADING]({ commit }, withMusk) {
    commit(mutations.UPDATE_GLOBAL_LOADING_STATUS, { status: true, withMusk });
  },
  [actions.HIDE_GLOBAL_LOADING]({ commit }) {
    commit(mutations.UPDATE_GLOBAL_LOADING_STATUS, { status: false });
  },
};

export default {
  state: moduleState,
  getters: moduleGetters,
  mutations: moduleMutations,
  actions: moduleActions,
};
