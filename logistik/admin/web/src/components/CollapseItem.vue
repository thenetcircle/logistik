<template>
  <div class="collapse-item" :class="{ 'is-active': isActived }">
    <header class="collapse-item__header" :aria-expanded="selected ? 'true' : 'fase'" @click="toggle">
      <p>{{ title }}</p>
      <span v-if="hasChildren" class="icon is-small"><i class="fa fa-chevron-right"></i></span>
    </header>
    <div ref="body" class="collapse-item__body">
      <slot></slot>
    </div>
</div>
</template>
<script>
import anime from 'animejs';

export default {
  props: {
    selected: Boolean,
    title: { type: String, required: true },
  },
  data() {
    return {
      isActived: this.selected,
      anime: null,
    };
  },
  computed: {
    el() {
      return this.$refs.body;
    },
    index() {
      return this.$parent.$collapseItems.indexOf(this);
    },
    hasChildren() {
      return this.$slots.default && this.$slots.default.length !== 0;
    },
  },
  created() {
    this.isCollapseItem = true;
  },
  mounted() {
    this.anime = anime({ target: this.el });
    this.$on('open', this.$parent.openByIndex);

    if (this.isActived) {
      this.$emit('open', this.index);
    } else {
      this.el.style.display = 'none';
    }
  },
  beforeDestroy() {
    anime.remove(this.el);
    this.$off('open', this.$parent.openByIndex);
  },
  methods: {
    toggle() {
      if (this.hasChildren) {
        if (!this.isActived) {
          this.active();
          this.$emit('open', this.index);
        } else {
          this.disactive();
        }
      }

      this.$emit('click');
    },
    active() {
      this.isActived = true;
      this.el.removeAttribute('style');

      anime({
        targets: this.el,
        duration: 337,
        easing: 'easeOutExpo',
        opacity: [0, 1],
        height: [0, this.el.scrollHeight],
        complete: () => {
          this.el.removeAttribute('style');
        },
      });
    },
    disactive() {
      if (this.isActived) {
        this.isActived = false;
        anime({
          targets: this.el,
          duration: 337,
          easing: 'easeOutExpo',
          opacity: [1, 0],
          height: [this.el.scrollHeight, 0],
          complete: () => {
            this.el.style.display = 'none';
          },
        });
      }
    },
  },
};
</script>

