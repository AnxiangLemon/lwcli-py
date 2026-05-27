/**
 * 插件设置面板宿主 SDK：在 iframe 内通过统一 API 读写 config/plugins.json。
 */
(function (global) {
  'use strict';

  function pluginIdFromPath() {
    var m = (global.location.pathname || '').match(/\/plugin-ui\/([^/]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function apiBase(pluginId) {
    return '/api/plugins/' + encodeURIComponent(pluginId) + '/settings';
  }

  async function fetchJson(url, options) {
    var res = await fetch(url, Object.assign({ credentials: 'same-origin' }, options || {}));
    var data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }
    if (!res.ok) {
      var msg = (data && data.error) || res.statusText || '请求失败';
      throw new Error(msg);
    }
    return data;
  }

  function createClient(pluginId) {
    var id = pluginId || pluginIdFromPath();
    if (!id) {
      throw new Error('无法解析 plugin_id');
    }
    var base = apiBase(id);
    return {
      pluginId: id,
      getSettings: function () {
        return fetchJson(base).then(function (d) {
          return d.settings || {};
        });
      },
      putSettings: function (patch) {
        return fetchJson(base, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch || {}),
        }).then(function (d) {
          return d.settings || {};
        });
      },
      testSettings: function (patch) {
        return fetchJson(base + '/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch || {}),
        });
      },
      listModels: function (patch) {
        return fetchJson(base + '/models', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch || {}),
        });
      },
      clearContext: function (patch) {
        return fetchJson(base + '/clear-context', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch || {}),
        });
      },
    };
  }

  global.LwPluginHost = {
    pluginIdFromPath: pluginIdFromPath,
    createClient: createClient,
    SECRET_MASK: '****************',
  };
})(typeof window !== 'undefined' ? window : globalThis);
