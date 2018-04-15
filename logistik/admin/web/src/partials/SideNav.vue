<template>
  <aside ref="menu" class="aside" @click="closeMenuOnMobile">
    <a class="aside__burger" @click.stop="openMenuOnMobile"><span class="icon"><i class="fa fa-bars"></i></span></a>
    <nav @click.stop="() => {}">
      <div class="aside__logo"></div>
      <div class="aside__nav-item">
        <collapse accordion>
          <collapse-item v-for="item of menu.items" :key="item.label" :title="item.label" @click="tryNavigate(item)">
            <template v-if="item.children">
              <a class="nav-item__subitem" v-for="child of item.children" :key="child.label" @click="tryNavigate(child)">{{child.label}}</a>
            </template>
          </collapse-item>
        </collapse>
      </div>
    </nav>
  </aside>
</template>
<script>
import { debounce } from 'lodash/function';
import Collapse from '@/components/Collapse';
import CollapseItem from '@/components/CollapseItem';

export default {
  components: { Collapse, CollapseItem },
  props: {
    menu: { type: Object, default: () => ({ items: [] }) },
    fixed: { type: Boolean, default: false },
  },
  data() {
    return {
      active: false,
      onResize: null,
      isMobileView: false,
    };
  },
  mounted() {
    this.onResize = debounce(this.adapt, 150, { maxWait: 1000 });
    window.addEventListener('resize', this.onResize);
    this.adapt();
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.onResize);
  },
  methods: {
    closeMenuOnMobile() {
      if (this.active) {
        this.active = false;
        this.$refs.menu.classList.remove('is-active');
        setTimeout(() => {
          this.$refs.menu.classList.remove('is-animating');
        }, 330);
      }
    },
    openMenuOnMobile() {
      if (!this.active) {
        this.active = true;
        this.$refs.menu.classList.add('is-animating', 'is-active');
      }
    },
    adapt() {
      if (window.innerWidth < 769) {
        this.isMobileView = true;
        if (this.fixed) {
          this.$refs.menu.classList.remove('fixed');
          document.querySelector('#app').classList.remove('has-fixed-side-nav');
        }
      } else {
        this.isMobileView = false;
        if (this.fixed) {
          this.$refs.menu.classList.add('fixed');
          document.querySelector('#app').classList.add('has-fixed-side-nav');
        }
      }
    },
    tryNavigate(item) {
      if (item.link) {
        location.href = item.link;
      }

      if (item.name) {
        if (this.isMobileView) {
          this.closeMenuOnMobile();
        }
        this.$router.push({ name: item.name });
      }
    },
  },
};
</script>
