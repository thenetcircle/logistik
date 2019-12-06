<template>
  <div class="modal" ref="modal">
    <div ref="background" class="modal-background" @click="dismiss"></div>
    <div ref="content" :class="isCard ? 'modal-card' : 'modal-content'">
      <slot name="content"></slot>
    </div>
  </div>
</template>
<script>
import anime from 'animejs'

export default {
  props: {
    active: { type: Boolean, required: true },
    dismissable: { type: Boolean, default: true },
    isCard: { type: Boolean, default: false },
    duration: { type: Number, default: 500 }
  },
  data () {
    return {
      open: false
    }
  },
  methods: {
    dismiss () {
      if (this.open && this.dismissable) {
        this.hide()
      }
    },
    show () {
      if (this.open) {
        return
      }
      this.open = true
      anime({
        targets: this.$refs.background,
        opacity: [0, 0.5],
        duration: this.duration,
        easing: 'linear',
        begin: () => {
          document.body.style.overflow = 'hidden'
          this.$refs.modal.style.display = 'flex'
        }
      })
      anime({
        targets: this.$refs.content,
        scale: [0, 1],
        easing: 'easeInOutSine',
        duration: this.duration
      })
    },
    hide () {
      if (!this.open) {
        return
      }
      this.open = false
      anime({
        targets: this.$refs.background,
        opacity: [0.5, 0],
        duration: 300,
        easing: 'linear'
      })
      anime({
        targets: this.$refs.content,
        scale: [1, 0],
        easing: 'easeInBack',
        duration: 300,
        complete: () => {
          document.body.style.removeProperty('overflow')
          this.$refs.modal.style.display = 'none'
          this.$emit('close')
        }
      })
    }
  },
  watch: {
    active (val) {
      if (val) {
        this.show()
      } else {
        this.hide()
      }
    }
  }
}
</script>
