<template>
  <label class="switch">
    <input type="checkbox" v-model="value" :disabled="disabled">
    <span class="slider"></span>
  </label>
</template>
<script>
export default {
  model: {
    prop: 'checked',
    event: 'change'
  },
  props: {
    checked: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false }
  },
  data () {
    return {
      value: this.checked
    }
  },
  watch: {
    value (val) {
      this.$emit('switch', val)
      this.$emit('change', val)
    }
  }
}
</script>
