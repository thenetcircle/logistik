import * as actions from '@/store/actions';

export default {
  methods: {
    showGlobalLoading (withMusk) {
      this.$store.dispatch(actions.SHOW_GLOBAL_LOADING, withMusk);
    },
    hideGlobalLoading () {
      this.$store.dispatch(actions.HIDE_GLOBAL_LOADING);
    }
  }
}
