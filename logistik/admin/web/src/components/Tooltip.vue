<template>
  <div ref="wrapper" class="has-tooltip" @mouseover="show" @mouseout="hide">
    <slot></slot>
    <span ref="tooltip" class="tooltip">{{content}}</span>
  </div>
</template>
<script>
import anime from 'animejs';

export default {
  props: {
    position: { type: String, default: 'bottom' },
    content: { type: String, required: true },
    delay: { type: Number, default: 200 },
  },
  data() {
    return {
      isOpen: false,
      isHovered: false,
      enterDelayTimeout: null,
      leaveDelayTimeout: null,
    };
  },
  computed: {
    tooltip() {
      return this.$refs.tooltip;
    },
  },
  methods: {
    setPosition() {
      const rect = this.$refs.wrapper.getBoundingClientRect();
      const position = this[this.position](rect);
      this.tooltip.style.top = `${position.top}px`;
      this.tooltip.style.left = `${position.left}px`;
    },

    top(rect) {
      return {
        left: (rect.width - this.tooltip.getBoundingClientRect().width) / 2,
        top: -this.tooltip.getBoundingClientRect().height - 10,
      };
    },
    bottom(rect) {
      const result = this.top(rect);
      result.top = -result.top;
      return result;
    },
    left(rect) {
      return {
        left: -this.tooltip.getBoundingClientRect().width - 10,
        top: (rect.height - this.tooltip.getBoundingClientRect().height) / 2,
      };
    },
    right(rect) {
      return {
        left: rect.width + 10,
        top: (rect.height - this.tooltip.getBoundingClientRect().height) / 2,
      };
    },
    show() {
      this.isHovered = true;
      if (this.isOpen) {
        return;
      }
      this.isOpen = true;
      this.setPosition();
      clearTimeout(this.enterDelayTimeout);
      this.enterDelayTimeout = setTimeout(() => {
        if (this.isHovered) {
          if (this.anime) {
            this.anime.pause();
          }
          this.anime = anime({
            targets: this.tooltip,
            opacity: 1,
            easing: 'easeOutQuart',
            begin: () => {
              this.tooltip.style.visibility = 'visible';
            },
            duration: 500,
          });
        }
      }, this.delay);
    },
    hide() {
      this.isHovered = false;
      if (!this.isOpen) {
        return;
      }
      this.isOpen = false;
      clearTimeout(this.leaveDelayTimeout);
      this.leaveDelayTimeout = setTimeout(() => {
        if (!this.isHovered) {
          if (this.anime) {
            this.anime.pause();
          }
          this.anime = anime({
            targets: this.tooltip,
            opacity: 0,
            easing: 'easeInOutQuart',
            complete: () => {
              this.tooltip.style.visibility = 'hidden';
            },
            duration: 300,
          });
        }
      }, this.delay);
    },
  },
};
</script>
<style lang="scss">
.has-tooltip {
  position: relative;

  .tooltip {
    padding: 10px 8px;
    font-size: 1rem;
    background-color: #323232;
    border-radius: 5px;
    color: #fff;
    min-height: .75rem;
    line-height: 1rem;
    position: absolute;
    text-align: center;
    overflow: hidden;
    pointer-events: none;
    top: 0;
    left: 0;
    visibility: hidden;
    z-index: 500;
    opacity: 0;
    white-space: nowrap;
  }
}
</style>
