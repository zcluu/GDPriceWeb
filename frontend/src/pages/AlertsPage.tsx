import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, Pencil, Send, Trash2, X } from "lucide-react";
import { api } from "../api/endpoints";
import type { AlertRule } from "../api/types";
import PageHeader from "../components/PageHeader";
import { fmtMoney, fmtTime } from "../utils";

type RuleType =
  | "PRICE_ABOVE"
  | "PRICE_BELOW"
  | "POSITION_GAIN_PERCENT"
  | "POSITION_LOSS_PERCENT"
  | "WINDOW_RANGE_AMOUNT"
  | "RANGE_STEP_AMOUNT";

const ruleTypes: Array<{ value: RuleType; label: string; description: string }> = [
  { value: "PRICE_ABOVE", label: "价格高于目标", description: "当前金价大于或等于目标价时提醒。" },
  { value: "PRICE_BELOW", label: "价格低于目标", description: "当前金价小于或等于目标价时提醒。" },
  { value: "POSITION_GAIN_PERCENT", label: "持仓涨幅达到", description: "当前价相对持仓均价上涨到指定比例时提醒。" },
  { value: "POSITION_LOSS_PERCENT", label: "持仓跌幅达到", description: "当前价相对持仓均价下跌到指定比例时提醒。" },
  { value: "WINDOW_RANGE_AMOUNT", label: "窗口价差达到", description: "最近一段时间内最高价与最低价的价差达标时提醒。" },
  { value: "RANGE_STEP_AMOUNT", label: "阶梯价差提醒", description: "以基准价为中心，向上或向下每隔固定金额触发一次提醒。" }
];

const windowOptions = [
  { value: "60", label: "近 1 分钟" },
  { value: "300", label: "近 5 分钟" },
  { value: "600", label: "近 10 分钟" },
  { value: "900", label: "近 15 分钟" },
  { value: "1800", label: "近 30 分钟" }
];

const defaultForm = {
  type: "RANGE_STEP_AMOUNT" as RuleType,
  target_price: "",
  target_percent: "",
  target_amount: "2",
  window_seconds: "300",
  cooldown_seconds: "600",
  enabled: true
};

type RuleForm = typeof defaultForm;

function ruleTypeLabel(type: string) {
  return ruleTypes.find((item) => item.value === type)?.label || type;
}

function signedLevel(value: number) {
  if (value > 0) return `+${value}`;
  return `${value}`;
}

function toInputValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function formFromRule(rule: AlertRule): RuleForm {
  return {
    type: rule.type as RuleType,
    target_price: toInputValue(rule.target_price),
    target_percent: toInputValue(rule.target_percent),
    target_amount: toInputValue(rule.target_amount),
    window_seconds: toInputValue(rule.window_seconds) || "300",
    cooldown_seconds: toInputValue(rule.cooldown_seconds) || "600",
    enabled: rule.enabled
  };
}

function buildRuleName(form: RuleForm) {
  const windowLabel = windowOptions.find((item) => item.value === form.window_seconds)?.label || "指定窗口";
  if (form.type === "PRICE_ABOVE") return `金价高于 ${form.target_price || "-"} 元提醒`;
  if (form.type === "PRICE_BELOW") return `金价低于 ${form.target_price || "-"} 元提醒`;
  if (form.type === "POSITION_GAIN_PERCENT") return `持仓上涨 ${form.target_percent || "-"}% 提醒`;
  if (form.type === "POSITION_LOSS_PERCENT") return `持仓下跌 ${form.target_percent || "-"}% 提醒`;
  if (form.type === "WINDOW_RANGE_AMOUNT") return `${windowLabel}价差达到 ${form.target_amount || "-"} 元提醒`;
  return `基准 ${form.target_price || "-"} 元每 ${form.target_amount || "-"} 元阶梯提醒`;
}

function ladderMarks(baseValue: string, stepValue: string) {
  const base = Number(baseValue);
  const step = Number(stepValue);
  if (!Number.isFinite(base) || !Number.isFinite(step) || step <= 0) return [];
  return [-2, -1, 0, 1, 2].map((level) => ({ level, price: base + step * level }));
}

function ruleMeta(rule: AlertRule) {
  if (rule.type === "PRICE_ABOVE" || rule.type === "PRICE_BELOW") {
    return rule.target_price ? [`目标 ${fmtMoney(rule.target_price)} 元`] : [];
  }
  if (rule.type === "POSITION_GAIN_PERCENT" || rule.type === "POSITION_LOSS_PERCENT") {
    return rule.target_percent ? [`比例 ${fmtMoney(rule.target_percent)}%`] : [];
  }
  if (rule.type === "WINDOW_RANGE_AMOUNT") {
    const items = [];
    if (rule.target_amount) items.push(`价差 ${fmtMoney(rule.target_amount)} 元`);
    if (rule.window_seconds) items.push(`窗口 ${rule.window_seconds / 60} 分钟`);
    return items;
  }
  if (rule.type === "RANGE_STEP_AMOUNT") {
    const items = [];
    if (rule.target_price) items.push(`基准 ${fmtMoney(rule.target_price)} 元`);
    if (rule.target_amount) items.push(`每 ${fmtMoney(rule.target_amount)} 元一档`);
    const level = rule.state?.last_step_index;
    if (typeof level === "number") items.push(`当前 ${signedLevel(level)} 档`);
    return items;
  }
  return [];
}

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const rulesQuery = useQuery({ queryKey: ["rules"], queryFn: api.rules });
  const eventsQuery = useQuery({ queryKey: ["events"], queryFn: api.events });
  const [form, setForm] = useState(defaultForm);
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);

  const currentRuleType = ruleTypes.find((item) => item.value === form.type) || ruleTypes[0];
  const generatedName = useMemo(() => buildRuleName(form), [form]);
  const previewMarks = useMemo(() => ladderMarks(form.target_price, form.target_amount), [form.target_price, form.target_amount]);

  const createMutation = useMutation({
    mutationFn: () => api.createRule(buildRulePayload()),
    onSuccess: () => {
      setForm(defaultForm);
      queryClient.invalidateQueries({ queryKey: ["rules"] });
    }
  });
  const updateMutation = useMutation({
    mutationFn: () => {
      if (!editingRuleId) {
        throw new Error("未选择要修改的规则");
      }
      return api.updateRule(editingRuleId, buildRulePayload());
    },
    onSuccess: () => {
      setEditingRuleId(null);
      setForm(defaultForm);
      queryClient.invalidateQueries({ queryKey: ["rules"] });
    }
  });
  const deleteMutation = useMutation({
    mutationFn: api.deleteRule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] })
  });
  const testMutation = useMutation({ mutationFn: () => api.testDingTalk() });

  function buildRulePayload() {
      const isPriceRule = form.type === "PRICE_ABOVE" || form.type === "PRICE_BELOW";
      const isPositionRule = form.type === "POSITION_GAIN_PERCENT" || form.type === "POSITION_LOSS_PERCENT";
      const isWindowRule = form.type === "WINDOW_RANGE_AMOUNT";
      const isStepRule = form.type === "RANGE_STEP_AMOUNT";
      return {
        name: generatedName,
        type: form.type,
        target_price: isPriceRule || isStepRule ? form.target_price || null : null,
        target_percent: isPositionRule ? form.target_percent || null : null,
        target_amount: isWindowRule || isStepRule ? form.target_amount || null : null,
        window_seconds: isWindowRule ? Number(form.window_seconds) : null,
        cooldown_seconds: Number(form.cooldown_seconds),
        reset_threshold_amount: null,
        trigger_mode: isStepRule ? "CROSS_EACH_STEP" : null,
        step_thresholds: null,
        enabled: form.enabled
      };
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (editingRuleId) {
      updateMutation.mutate();
    } else {
      createMutation.mutate();
    }
  }

  function changeType(type: RuleType) {
    setForm((current) => ({
      ...current,
      type,
      target_amount: type === "RANGE_STEP_AMOUNT" && !current.target_amount ? "2" : current.target_amount
    }));
  }

  function editRule(rule: AlertRule) {
    setEditingRuleId(rule.id);
    setForm(formFromRule(rule));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function resetForm() {
    setEditingRuleId(null);
    setForm(defaultForm);
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const saveError = createMutation.error || updateMutation.error;

  return (
    <div className="page">
      <PageHeader
        title="提醒规则"
        subtitle="固定价格、持仓涨跌幅、短时异动和阶梯价差都在这里配置。"
        actions={
          <button className="ghost-button" onClick={() => testMutation.mutate()}>
            <Send size={16} />
            测试钉钉
          </button>
        }
      />

      <section className="two-column">
        <form className="panel rule-form" onSubmit={submit}>
          <div className="panel-title">
            <BellRing size={18} />
            {editingRuleId ? "编辑规则" : "新建规则"}
          </div>
          {editingRuleId && (
            <div className="edit-banner">
              <span>正在修改 #{editingRuleId}，保存后会覆盖原规则配置。</span>
              <button type="button" className="tiny-button" onClick={resetForm}>
                <X size={14} />
                取消
              </button>
            </div>
          )}

          <label>
            提醒类型
            <select value={form.type} onChange={(event) => changeType(event.target.value as RuleType)}>
              {ruleTypes.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <div className="rule-name-preview">
            <span>规则名称</span>
            <strong>{generatedName}</strong>
            <small>{currentRuleType.description}</small>
          </div>

          {(form.type === "PRICE_ABOVE" || form.type === "PRICE_BELOW") && (
            <div className="rule-fieldset">
              <label>
                目标价格
                <input
                  required
                  value={form.target_price}
                  onChange={(event) => setForm({ ...form, target_price: event.target.value })}
                  placeholder="780"
                />
              </label>
            </div>
          )}

          {(form.type === "POSITION_GAIN_PERCENT" || form.type === "POSITION_LOSS_PERCENT") && (
            <div className="rule-fieldset">
              <label>
                目标比例
                <input
                  required
                  value={form.target_percent}
                  onChange={(event) => setForm({ ...form, target_percent: event.target.value })}
                  placeholder="5"
                />
              </label>
            </div>
          )}

          {form.type === "WINDOW_RANGE_AMOUNT" && (
            <div className="rule-fieldset form-grid">
              <label>
                价差金额
                <input
                  required
                  value={form.target_amount}
                  onChange={(event) => setForm({ ...form, target_amount: event.target.value })}
                  placeholder="5"
                />
              </label>
              <label>
                时间窗口
                <select
                  value={form.window_seconds}
                  onChange={(event) => setForm({ ...form, window_seconds: event.target.value })}
                >
                  {windowOptions.map((item) => (
                    <option value={item.value} key={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {form.type === "RANGE_STEP_AMOUNT" && (
            <div className="step-editor">
              <div className="form-grid">
                <label>
                  基准价格
                  <input
                    required
                    value={form.target_price}
                    onChange={(event) => setForm({ ...form, target_price: event.target.value })}
                    placeholder="1000"
                  />
                </label>
                <label>
                  阶梯间隔
                  <input
                    required
                    value={form.target_amount}
                    onChange={(event) => setForm({ ...form, target_amount: event.target.value })}
                    placeholder="2"
                  />
                </label>
              </div>
              <div className="ladder-preview">
                <span>预览价位</span>
                <div>
                  {previewMarks.length ? (
                    previewMarks.map((mark) => (
                      <strong className={mark.level === 0 ? "center" : ""} key={mark.level}>
                        {fmtMoney(mark.price)}
                      </strong>
                    ))
                  ) : (
                    <small>填写基准价格和阶梯间隔后生成</small>
                  )}
                </div>
              </div>
              <div className="rule-preview">
                价格穿过任意预览价位时发送提醒；例如基准 1000、间隔 2，会监听 996、998、1000、1002、1004 等价位。
              </div>
            </div>
          )}

          <div className="form-grid">
            <label>
              冷却时间
              <input
                value={form.cooldown_seconds}
                onChange={(event) => setForm({ ...form, cooldown_seconds: event.target.value })}
                placeholder="600"
              />
            </label>
          </div>

          <label className="switch-line">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => setForm({ ...form, enabled: event.target.checked })}
            />
            {editingRuleId ? "规则保持启用" : "创建后立即启用"}
          </label>
          {saveError && <div className="form-error">{saveError.message}</div>}
          <button className="primary-button full" disabled={isSaving}>
            {isSaving ? "正在保存" : editingRuleId ? "保存修改" : "保存规则"}
          </button>
        </form>

        <div className="panel wide">
          <div className="panel-toolbar">
            <div>
              <h2>现有规则</h2>
              <p>{rulesQuery.data?.length || 0} 条规则</p>
            </div>
          </div>
          <div className="rule-list">
            {(rulesQuery.data || []).map((rule) => (
              <div className="rule-card" key={rule.id}>
                <div>
                  <strong>{rule.name}</strong>
                  <span>{ruleTypeLabel(rule.type)}</span>
                </div>
                <div className="rule-meta">
                  {ruleMeta(rule).map((item) => (
                    <span key={item}>{item}</span>
                  ))}
                  <span>{rule.enabled ? "启用中" : "已停用"}</span>
                </div>
                <div className="rule-actions">
                  <button className="icon-button" onClick={() => editRule(rule)} title="编辑">
                    <Pencil size={16} />
                  </button>
                  <button className="icon-button" onClick={() => deleteMutation.mutate(rule.id)} title="删除">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-toolbar">
          <div>
            <h2>提醒事件</h2>
            <p>最近发送和记录的提醒</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>规则</th>
                <th>价格</th>
                <th>触发信息</th>
                <th>发送状态</th>
              </tr>
            </thead>
            <tbody>
              {(eventsQuery.data || []).slice(0, 12).map((event) => (
                <tr key={event.id}>
                  <td>{fmtTime(event.created_at)}</td>
                  <td>{event.rule_name}</td>
                  <td>{fmtMoney(event.price)} 元</td>
                  <td>
                    {event.triggered_level !== null
                      ? `${signedLevel(event.triggered_level)} 档`
                      : event.window_range
                        ? `价差 ${fmtMoney(event.window_range)} 元`
                        : "-"}
                  </td>
                  <td>{event.sent ? "已发送" : "未发送"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
