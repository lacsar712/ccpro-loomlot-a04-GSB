<script>
  import { onMount } from 'svelte';
  import { api, toLocalInput, fromLocalInput } from '../lib/api.js';
  import { user } from '../lib/auth.js';

  let lots = [];
  let vats = [];
  let rows = [];
  let error = '';
  let form = {
    dyeLotId: '',
    defectNote: '',
    openedAt: toLocalInput(new Date().toISOString()),
  };

  $: isSupervisor = $user?.role === 'admin';

  async function load() {
    error = '';
    try {
      [lots, vats, rows] = await Promise.all([
        api('/dye-lots'),
        api('/vats'),
        api('/rework-tickets'),
      ]);
      if (!form.dyeLotId && lots.length) form.dyeLotId = String(lots[0].id);
    } catch (e) {
      error = e.message;
    }
  }

  onMount(load);

  function lotLabel(id) {
    const lot = lots.find((x) => x.id === id);
    if (!lot) return `#${id}`;
    const vat = vats.find((v) => v.id === lot.vatId);
    return vat ? `${lot.recipeName} (#${lot.id} · ${vat.vatCode})` : `${lot.recipeName} (#${lot.id})`;
  }

  async function openTicket() {
    error = '';
    if (form.defectNote.trim().length < 8) {
      error = '缺陷说明至少 8 个字';
      return;
    }
    try {
      await api('/rework-tickets', {
        method: 'POST',
        body: JSON.stringify({
          dyeLotId: Number(form.dyeLotId),
          defectNote: form.defectNote.trim(),
          openedAt: fromLocalInput(form.openedAt),
        }),
      });
      form.defectNote = '';
      form.openedAt = toLocalInput(new Date().toISOString());
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  async function closeTicket(id) {
    error = '';
    try {
      await api(`/rework-tickets/${id}/close`, { method: 'POST' });
      await load();
    } catch (e) {
      error = e.message;
    }
  }
</script>

<h1 class="page-title">回修复染</h1>
<p class="page-sub">
  复染单挂原染程；同一原染程未结案不可重复开单。结案需原染程上至少两条色牢度抽检，且较新一条耐洗等级不低于较旧一条（仅主管可结案）。
</p>

<div class="panel" style="margin-bottom:1rem;">
  <div class="form-grid">
    <label
      >原染程
      <select bind:value={form.dyeLotId}>
        {#each lots as lot}
          <option value={String(lot.id)} disabled={lot.hasOpenRework}>
            {lot.recipeName} (#{lot.id}){lot.hasOpenRework ? ' · 已有未结案复染' : ''}
          </option>
        {/each}
      </select>
    </label>
    <label>开单时刻 <input type="datetime-local" bind:value={form.openedAt} /></label>
    <label class="wide">缺陷说明（至少 8 字）<input bind:value={form.defectNote} /></label>
  </div>
  <div class="toolbar">
    <button class="btn" type="button" on:click={openTicket}>开复染单</button>
    <span class="who-note">开单人：{$user?.displayName || $user?.username || ''}（操作员可开单）</span>
  </div>
  {#if error}<p class="err">{error}</p>{/if}
</div>

<div class="panel">
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>原染程</th>
        <th>缺陷说明</th>
        <th>开单时刻</th>
        <th>开单人</th>
        <th>结案时刻</th>
        <th>状态</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{lotLabel(row.dyeLotId)}</td>
          <td>{row.defectNote}</td>
          <td>{new Date(row.openedAt).toLocaleString()}</td>
          <td>{row.openerName}</td>
          <td>{row.closedAt ? new Date(row.closedAt).toLocaleString() : '—'}</td>
          <td>
            {#if row.closedAt}
              <span class="badge ready">已结案</span>
            {:else}
              <span class="badge rework">未结案</span>
            {/if}
          </td>
          <td class="row-actions">
            {#if !row.closedAt}
              {#if isSupervisor}
                <button class="btn ghost small" type="button" on:click={() => closeTicket(row.id)}>
                  主管结案
                </button>
              {:else}
                <span class="who-note">仅主管结案</span>
              {/if}
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .wide {
    grid-column: 1 / -1;
  }

  .who-note {
    font-size: 0.78rem;
    color: var(--indigo-mist);
  }
</style>
