<template>
  <div id="app">
      <div class="global-loading" v-show="isGlobalLoadingShowing">
        <div class="global-loading__musk" v-show="isLoadingMuskShowing"></div>
        <loading class="global-loading__loading"></loading>
      </div>
      <navigator />
      <main class="container" :class="{ home: isHome }">
        <transition name="fade" mode="out-in">
          <router-view></router-view>
        </transition>
      </main>
      <i-footer></i-footer>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import Loading from '@/components/Loading'
import Navigator from '@/partials/Navigator'
import IFooter from '@/partials/Footer'
import globalLoading from '@/mixins/globalLoading'

export default {
  components: { Loading, Navigator, IFooter },
  mixins: [globalLoading],
  computed: {
    ...mapGetters(['isGlobalLoadingShowing', 'isLoadingMuskShowing']),
    isHome () {
      return this.$route.name === 'home'
    }
  }
}
</script>
