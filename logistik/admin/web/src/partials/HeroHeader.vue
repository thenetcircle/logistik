<template>
  <header class="hero-header" :class="{ 'snap': isOverThreshold, 'tall-header': isTallHeader }">
    <div class="header-content container">
      <div class="header-content__logo-large" :class="{ 'hide': !isTallHeader }">
        <p class="is-size-2">Dino Admin <span class="is-size-5">{{env}}</span></p>
      </div>
      <div class="header-content__logo" :class="{ 'hide': isTallHeader && !isOverThreshold }">
        <p class="is-size-6">Dino Admin - {{env}}</p>
      </div>
      <div ref="menu" class="header-content__menu">
        <div class="menu-item" v-for="item of menu.items" :key="item.label" :class="{ 'is-active': activeId === item.id }">
          <div class="menu-item__label"
               :class="{ 'has-children': item.children }"
              @click="tryNavigate(item)">{{item.label}}</div>
          <ul v-if="item.children" class="menu-item__children">
            <li class="menu-item__child-item"
                v-for="child of item.children"
                :key="child.label"
                @click="tryNavigate(child, item.id)">{{child.label}}</li>
          </ul>
        </div>
      </div>
    </div>
  </header>
</template>
<script>
import config from '@/config'

export default {
  props: {
    menu: { type: Object, default: () => ({ items: [] }) },
    fixed: { type: Boolean, default: false }
  },
  data () {
    return {
      scrollY: 0,
      activeId: 0
    }
  },
  computed: {
    isOverThreshold () {
      return this.scrollY > 128
    },
    isHome () {
      return this.$route && this.$route.name === 'home'
    },
    isTallHeader () {
      return this.isHome && !this.fixed
    },
    env () {
      return config.environment
    },
    version () {
      return config.version
    }
  },
  mounted () {
    this.listeningOnScroll()
  },
  methods: {
    listeningOnScroll () {
      window.addEventListener('scroll', this.manipulateScrollY)
    },
    manipulateScrollY () {
      this.scrollY = window.scrollY
    },
    tryNavigate (item, id) {
      if (item.link) {
        location.href = item.link
      }

      if (item.name) {
        this.activeId = id || item.id || 1
        this.$router.push({ name: item.name })
      }
    }
  }
}
</script>
