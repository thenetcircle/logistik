import Vue from 'vue'
import Router from 'vue-router'
import Main from '@/pages/Main'
import Model from '@/pages/Model'
import Overview from '@/pages/Overview'
import config from '@/config'

Vue.use(Router)

const router = new Router({
  mode: 'history',
  routes: [
    {
      path: config.base,
      component: Main,
      children: [
        { path: config.base, name: 'home', component: Overview },
        { path: 'model', name: 'model', component: Model }
      ]
    },
    {
      path: '*',
      redirect: { name: 'home' }
    }
  ]
})

export default router
