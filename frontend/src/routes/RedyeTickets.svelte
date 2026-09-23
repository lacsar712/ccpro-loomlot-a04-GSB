<script>
  import { onMount } from 'svelte';
  import { api, VAT_STATUS } from '../lib/api.js';
  import { user } from '../lib/auth.js';

  let lots = [];
  let vats = [];
  let rows = [];
  let error = '';
  let showClosed = false;
  let form = {
    dyeLotId: '',
    defectDesc: '',
  };
  let saving = false;

  $: isAdmin = $user?.role === 'admin';

  async function load() {
    error = '';
    try {
      const query = showClosed ? '' : '?open=true';
      [vats, lots, rows] = await Promise.all([
        api('/vats'),
        api('/dye-lots'),
        api(`/redye-tickets${query}`),
      ]);
      if (!form.dyeLotId && lots.length) form.dyeLotId = String(lots[0].id);
    } catch (e) {
      error = e.message;
    }
  }

  onMount(load);

  function lotLabel(id) {
    const lot = lots.find((x) => x.id === id);
    return lot ? `#${lot.id} ${lot.recipeName}` : `#${id}`;
  }

  function vatOfLot(lotId) {
    const lot = lots.find((x) => x.id === lotId);
    if (!lot) return null;
    return vats.find((v) => v.id === lot.vatId) || null;
  }

  async function openTicket() {
    error = '';
    const desc = form.defectDesc.trim();
    if (desc.length < 8) {
      error = '缺陷说明至少 8 个字';
      return;
    }
    saving = true;
    try {
      await api('/redye-tickets', {
        method: 'POST',
        body: JSON.stringify({ dyeLotId: Number(form.dyeLotId), defectDesc: desc }),
      });
      form.defectDesc = '';
      await load();
    } catch (e) {
      error = e.message;
    } finally {
      saving = false;
    }
  }

  async function closeTicket(id) {
    if (!confirm('确认结案该回修复染单？将校验原染程双检色牢度。')) return;
    error = '';
    try {
      await api(`/redye-tickets/${id}/close`, { method: 'POST' });
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  function fmt(iso) {
    return iso ? new Date(iso).toLocaleString() : '—';
  }
</script>

<h1 class="page-title">回修复染</h1>
<p class="page-sub">
  复染挂原染程并锁定其染缸；同一原染程未结案不可再开。结案须原染程双检色牢度（最新耐洗等级不低于上一条），仅主管可结案。
</p>

<div class="panel" style="margin-bottom:1rem;">
  <div class="form-grid">
    <label
      >原染程
      <select bind:value={form.dyeLotId}>
        {#each lots as lot}
          <option value={String(lot.id)}>#{lot.id} {lot.recipeName} · {lot.fabricKg}kg</option>
        {/each}
      </select>
    </label>
    <label class="wide"
      >缺陷说明（至少 8 字）
      <textarea rows="2" bind:value={form.defectDesc} placeholder="如：左幅色花、边中色差超标…"></textarea>
    </label>
  </div>
  <div class="toolbar">
    <button class="btn" type="button" disabled={saving} on:click={openTicket}>
      {saving ? '开立中…' : '开立复染单'}
    </button>
    <span class="hint">操作员可开单 · 结案仅主管</span>
  </div>
  {#if error}<p class="err">{error}</p>{/if}
</div>

<div class="panel">
  <div class="toolbar">
    <label class="inline">
      <input type="checkbox" bind:checked={showClosed} on:change={load} />
      显示已结案
    </label>
  </div>
  <table>
    <thead>
      <tr>
        <th>单号</th>
        <th>原染程</th>
        <th>染缸</th>
        <th>缺陷说明</th>
        <th>开单时刻</th>
        <th>开单人</th>
        <th>结案时刻</th>
        <th>结案人</th>
        <th>状态</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr class:openrow={!row.closedAt}>
          <td>{row.id}</td>
          <td>{lotLabel(row.dyeLotId)}</td>
          <td>
            {#if vatOfLot(row.dyeLotId)}
              {@const v = vatOfLot(row.dyeLotId)}
              {v.vatCode}
              <span class="badge {v.status}">{VAT_STATUS[v.status] || v.status}</span>
            {:else}
              #{row.vatId}
            {/if}
          </td>
          <td class="desc">{row.defectDesc}</td>
          <td>{fmt(row.openedAt)}</td>
          <td>{row.openerName}</td>
          <td>{fmt(row.closedAt)}</td>
          <td>{row.closerName || '—'}</td>
          <td>
            {#if row.closedAt}
              <span class="badge closed">已结案</span>
            {:else}
              <span class="badge open">未结案</span>
            {/if}
          </td>
          <td class="row-actions">
            {#if !row.closedAt}
              {#if isAdmin}
                <button class="btn small" type="button" on:click={() => closeTicket(row.id)}>结案</button>
              {:else}
                <span class="hint">主管结案</span>
              {/if}
            {/if}
          </td>
        </tr>
      {/each}
      {#if rows.length === 0}
        <tr><td colspan="10" class="empty">暂无复染单</td></tr>
      {/if}
    </tbody>
  </table>
</div>

<style>
  .wide {
    grid-column: 1 / -1;
  }

  .inline {
    flex-direction: row;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.85rem;
  }

  .hint {
    color: var(--indigo-mist);
    font-size: 0.78rem;
  }

  .desc {
    max-width: 220px;
  }

  .openrow {
    background: rgba(212, 101, 122, 0.06);
  }

  .badge.open {
    color: var(--danger);
    border-color: rgba(212, 101, 122, 0.5);
    background: rgba(212, 101, 122, 0.12);
  }

  .badge.closed {
    color: var(--ok);
    border-color: rgba(76, 175, 130, 0.45);
  }

  .empty {
    text-align: center;
    color: var(--indigo-mist);
    padding: 1.2rem;
  }
</style>
