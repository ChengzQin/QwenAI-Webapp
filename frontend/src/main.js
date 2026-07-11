// src/main.js
import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import App from './App.vue';
import './styles/global.css';

const app = createApp(App);
app.use(ElementPlus);
app.mount('#app');