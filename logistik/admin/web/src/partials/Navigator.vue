<template>
  <nav :class="{ 'has-fixed-aside': hasFixedAside }">
    <hero :menu="menu" :fixed="hasFixedAside"></hero>
    <side-nav :menu="menu" :fixed="hasFixedAside"></side-nav>
  </nav>
</template>
<script>
import Hero from '@/partials/HeroHeader';
import SideNav from '@/partials/SideNav';
import MENU from '@/config/menu';

export default {
  components: { Hero, SideNav },
  data() {
    return {
      menu: MENU,
      hasFixedAside: false,
    };
  },
};
</script>
