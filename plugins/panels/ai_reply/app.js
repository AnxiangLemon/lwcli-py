(function () {
  'use strict';

  var MASK = (window.LwPluginHost && window.LwPluginHost.SECRET_MASK) || '****************';

  var PRESETS = {
    deepseek: {
      base_url: 'https://api.deepseek.com',
      chat_path: '/v1/chat/completions',
    },
    custom: {
      base_url: '',
      chat_path: '/v1/chat/completions',
    },
  };

  var api = LwPluginHost.createClient();
  var $ = function (id) {
    return document.getElementById(id);
  };

  var checkboxes = [
    'enabled',
    'reply_private',
    'reply_group',
    'use_context',
    'reply_on_error',
  ];

  var _apiKeyDirty = false;

  function isMaskValue(v) {
    if (!v || !String(v).trim()) return true;
    var s = String(v).trim();
    if (s === MASK) return true;
    return s.length >= 6 && /^[*•●·.]+$/.test(s);
  }

  function setStatus(msg, isErr) {
    var el = $('status');
    el.textContent = msg || '';
    el.className = 'status' + (isErr ? ' err' : ' ok');
  }

  function setTestStatus(msg, isErr) {
    var el = $('test_status');
    if (!el) return;
    el.textContent = msg || '';
    el.className = 'inline-status' + (isErr ? ' err' : msg ? ' ok' : '');
  }

  function mergeModelIds() {
    var seen = {};
    var out = [];
    function add(id) {
      id = (id || '').trim();
      if (!id || seen[id]) return;
      seen[id] = true;
      out.push(id);
    }
    for (var i = 0; i < arguments.length; i++) {
      var arg = arguments[i];
      if (!arg) continue;
      if (typeof arg === 'string') {
        add(arg);
        continue;
      }
      if (Array.isArray(arg)) {
        arg.forEach(add);
      }
    }
    return out;
  }

  function modelIdsFromSelect() {
    var sel = $('model_select');
    if (!sel) return [];
    var ids = [];
    for (var i = 0; i < sel.options.length; i++) {
      var v = sel.options[i].value;
      if (v) ids.push(v);
    }
    return ids;
  }

  function getModelValue() {
    var sel = $('model_select');
    if (!sel) return '';
    return (sel.value || '').trim();
  }

  function setModelValue(modelId) {
    var sel = $('model_select');
    if (!sel) return;
    modelId = (modelId || '').trim();
    if (!modelId) {
      sel.value = '';
      return;
    }
    for (var i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === modelId) {
        sel.selectedIndex = i;
        return;
      }
    }
  }

  function applyProviderPreset(provider, force) {
    var p = PRESETS[provider] || PRESETS.custom;
    if (force || !$('base_url').value.trim()) $('base_url').value = p.base_url;
    if (force || !$('chat_path').value.trim()) $('chat_path').value = p.chat_path;
    updateEndpointPreview();
  }

  function updateEndpointPreview() {
    var el = $('endpoint_preview');
    if (!el) return;
    var base = ($('base_url').value || '').trim().replace(/\/+$/, '');
    var path = ($('chat_path').value || '').trim();
    if (!path.startsWith('/')) path = '/' + path;
    el.textContent = (base || 'https://api.deepseek.com') + path;
  }

  function updateApiKeyHint(s) {
    var el = $('api_key_hint');
    if (!el) return;
    if (s && s.api_key_configured) {
      el.textContent = '已保存 Key（显示为 * 号；要更换请清空后输入新 Key）';
    } else {
      el.textContent = '';
    }
  }

  function fillApiKeyField(s) {
    var el = $('api_key');
    if (!el) return;
    _apiKeyDirty = false;
    if (s && (s.api_key_configured || isMaskValue(s.api_key))) {
      el.value = MASK;
      el.type = 'password';
    } else {
      el.value = '';
    }
  }

  function readApiKeyForSubmit() {
    var v = $('api_key').value.trim();
    if (isMaskValue(v)) return '';
    if (!_apiKeyDirty) return '';
    return v;
  }

  function readForm() {
    var data = {
      provider: $('provider').value,
      api_key: readApiKeyForSubmit(),
      use_full_url: false,
      base_url: $('base_url').value.trim(),
      chat_path: $('chat_path').value.trim(),
      model: getModelValue(),
      system_prompt: $('system_prompt').value.trim(),
      system_prompt_private: $('system_prompt_private').value.trim(),
      system_prompt_group: $('system_prompt_group').value.trim(),
      private_allow_wxids: $('private_allow_wxids').value.trim(),
      group_allow_wxids: $('group_allow_wxids').value.trim(),
      cached_model_ids: mergeModelIds(modelIdsFromSelect()),
      temperature: parseFloat($('temperature').value, 10),
      max_tokens: parseInt($('max_tokens').value, 10),
      timeout_sec: parseFloat($('timeout_sec').value, 10),
      max_context_turns: parseInt($('max_context_turns').value, 10),
      group_trigger: $('group_trigger').value,
      group_prefix: $('group_prefix').value.trim(),
      error_message: $('error_message').value.trim(),
    };
    checkboxes.forEach(function (k) {
      data[k] = $(k).checked;
    });
    return data;
  }

  function fillForm(s) {
    s = s || {};
    $('provider').value = s.provider || 'deepseek';
    fillApiKeyField(s);
    $('base_url').value = s.base_url || PRESETS.deepseek.base_url;
    $('chat_path').value = s.chat_path || PRESETS.deepseek.chat_path;
    fillModelSelect(mergeModelIds(s.cached_model_ids, s.model));
    setModelValue(s.model || '');
    var defaultPrompt = '你是一个友善、简洁的中文助手。';
    $('system_prompt').value = s.system_prompt || defaultPrompt;
    $('system_prompt_private').value = s.system_prompt_private || '';
    $('system_prompt_group').value = s.system_prompt_group || '';
    $('private_allow_wxids').value = s.private_allow_wxids || '';
    $('group_allow_wxids').value = s.group_allow_wxids || '';
    $('temperature').value = s.temperature != null ? s.temperature : 0.7;
    $('max_tokens').value = s.max_tokens != null ? s.max_tokens : 1024;
    $('timeout_sec').value = s.timeout_sec != null ? s.timeout_sec : 60;
    $('max_context_turns').value =
      s.max_context_turns != null ? s.max_context_turns : 6;
    $('group_trigger').value = s.group_trigger || 'at_only';
    $('group_prefix').value = s.group_prefix || '#';
    $('error_message').value =
      s.error_message || 'AI 暂时不可用，请稍后再试。';
    $('enabled').checked = s.enabled !== false;
    $('reply_private').checked = s.reply_private !== false;
    $('reply_group').checked = s.reply_group !== false;
    $('use_context').checked = s.use_context !== false;
    $('reply_on_error').checked = !!s.reply_on_error;
    updateApiKeyHint(s);
    updateEndpointPreview();
  }

  function appendSelectPlaceholder(sel, text, selected) {
    var ph = document.createElement('option');
    ph.value = '';
    ph.textContent = text;
    ph.disabled = true;
    if (selected) ph.selected = true;
    sel.appendChild(ph);
  }

  function fillModelSelect(models) {
    var sel = $('model_select');
    if (!sel) return;
    var keep = getModelValue();
    var list = mergeModelIds(models);
    sel.innerHTML = '';
    if (!list.length) {
      appendSelectPlaceholder(sel, '请先获取模型', true);
    } else {
      var hasKeep = keep && list.indexOf(keep) >= 0;
      appendSelectPlaceholder(sel, '请选择模型', !hasKeep);
      list.forEach(function (id) {
        var opt = document.createElement('option');
        opt.value = id;
        opt.textContent = id;
        sel.appendChild(opt);
      });
    }
    if (keep && list.indexOf(keep) >= 0) {
      sel.value = keep;
    } else if (!list.length) {
      sel.value = '';
    }
  }

  async function load() {
    setStatus('加载中…');
    try {
      var s = await api.getSettings();
      fillForm(s);
      setStatus('已加载');
    } catch (e) {
      setStatus(e.message || '加载失败', true);
    }
  }

  async function save() {
    setStatus('保存中…');
    try {
      await api.putSettings(readForm());
      var s = await api.getSettings();
      fillForm(s);
      setStatus('已保存，立即生效');
    } catch (e) {
      setStatus(e.message || '保存失败', true);
    }
  }

  async function testConn() {
    setTestStatus('测试连接中…');
    var btn = $('btn-test');
    if (btn) btn.disabled = true;
    try {
      var res = await api.testSettings(readForm());
      if (res.ok === false) throw new Error(res.error || '测试失败');
      setTestStatus('连接成功：' + (res.message || 'OK'));
    } catch (e) {
      setTestStatus(e.message || '测试失败', true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function fetchModels() {
    setTestStatus('正在获取模型列表…');
    var btn = $('btn-models');
    if (btn) btn.disabled = true;
    try {
      var res = await api.listModels(readForm());
      if (!res.ok) throw new Error(res.error || '获取失败');
      var models = mergeModelIds(res.models);
      if (!models.length) throw new Error('接口返回的模型列表为空');
      var keep = getModelValue();
      fillModelSelect(models);
      if (keep && models.indexOf(keep) >= 0) {
        $('model_select').value = keep;
      }
      setTestStatus(
        '已获取 ' + models.length + ' 个模型，请选择后点「保存」写入配置'
      );
    } catch (e) {
      var msg = e.message || '获取模型失败';
      if (msg === 'Not Found' || msg.indexOf('404') >= 0) {
        msg +=
          '（请确认已重启 LWAPI 服务，且 Base URL 为 https://api.deepseek.com）';
      }
      setTestStatus(msg, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  $('provider').addEventListener('change', function () {
    applyProviderPreset($('provider').value, true);
  });

  $('api_key').addEventListener('focus', function () {
    if (isMaskValue($('api_key').value)) {
      $('api_key').value = '';
      _apiKeyDirty = true;
    }
  });

  $('api_key').addEventListener('input', function () {
    _apiKeyDirty = true;
    if ($('api_key').value.trim() && $('provider').value === 'deepseek') {
      applyProviderPreset('deepseek', false);
    }
  });

  $('base_url').addEventListener('input', updateEndpointPreview);
  $('chat_path').addEventListener('input', updateEndpointPreview);

  async function clearContext() {
    var el = $('context_status');
    if (el) {
      el.textContent = '清空中…';
      el.className = 'inline-status context-status';
    }
    var btn = $('btn-clear-context');
    if (btn) btn.disabled = true;
    try {
      var res = await api.clearContext({});
      if (res.ok === false) throw new Error(res.error || '清空失败');
      if (el) {
        el.textContent = res.message || '已清空全部对话上下文';
        el.className = 'inline-status context-status ok';
      }
    } catch (e) {
      if (el) {
        el.textContent = e.message || '清空失败';
        el.className = 'inline-status context-status err';
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  $('btn-save').addEventListener('click', save);
  $('btn-reload').addEventListener('click', load);
  $('btn-test').addEventListener('click', testConn);
  $('btn-models').addEventListener('click', fetchModels);
  $('btn-clear-context').addEventListener('click', clearContext);

  load();
})();
