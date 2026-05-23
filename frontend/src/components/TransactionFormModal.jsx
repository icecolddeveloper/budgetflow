import { useState } from "react";

import { ModalShell } from "./ModalShell";

const transactionKinds = [
  { value: "deposit", label: "Income" },
  { value: "withdraw", label: "Expense" },
  { value: "transfer", label: "Allocate" },
];

const TRANSACTION_FIELDS = [
  "kind",
  "amount",
  "description",
  "source_category",
  "destination_category",
  "occurred_at",
];

function extractFieldErrors(data, fields) {
  if (!data || typeof data !== "object") {
    return {};
  }
  const result = {};
  for (const field of fields) {
    const value = data[field];
    if (Array.isArray(value)) {
      result[field] = value.map(String).join(" ");
    } else if (typeof value === "string") {
      result[field] = value;
    }
  }
  return result;
}

function formatLocalDateTime() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const localTime = new Date(now.getTime() - offset * 60000);
  return localTime.toISOString().slice(0, 16);
}

export function TransactionFormModal({ categories, onClose, onSubmit }) {
  const primaryCategory = categories.find((category) => category.is_primary);
  const primaryId = primaryCategory ? String(primaryCategory.id) : "";
  const fallbackId = categories[0]?.id ? String(categories[0].id) : "";

  const [form, setForm] = useState({
    kind: "deposit",
    amount: "",
    description: "",
    source_category: primaryId,
    destination_category: primaryId || fallbackId,
    occurred_at: formatLocalDateTime(),
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const sortedCategories = [...categories].sort((left, right) => left.name.localeCompare(right.name));

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => {
      if (name !== "kind") {
        return { ...current, [name]: value };
      }
      if (value === "deposit") {
        return { ...current, kind: value, source_category: "", destination_category: primaryId };
      }
      if (value === "withdraw") {
        return { ...current, kind: value, source_category: "", destination_category: "" };
      }
      return { ...current, kind: value, source_category: primaryId, destination_category: "" };
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const nextErrors = {};
    if (!form.amount || Number(form.amount) <= 0) {
      nextErrors.amount = "Enter an amount greater than zero.";
    }
    if (form.kind === "deposit" && !form.destination_category) {
      nextErrors.destination_category = "Choose a category to fund.";
    }
    if (form.kind === "withdraw" && !form.source_category) {
      nextErrors.source_category = "Choose a category to spend from.";
    }
    if (form.kind === "transfer") {
      if (!form.source_category) {
        nextErrors.source_category = "Choose a source category.";
      }
      if (!form.destination_category) {
        nextErrors.destination_category = "Choose a destination category.";
      }
      if (
        form.source_category &&
        form.destination_category &&
        form.source_category === form.destination_category
      ) {
        nextErrors.destination_category = "Choose a different destination category.";
      }
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const payload = {
      kind: form.kind,
      amount: Number(form.amount).toFixed(2),
      description: form.description,
      occurred_at: new Date(form.occurred_at).toISOString(),
      source_category: form.kind === "deposit" ? null : form.source_category || null,
      destination_category:
        form.kind === "withdraw" ? null : form.destination_category || null,
    };

    setSubmitting(true);
    try {
      await onSubmit(payload);
    } catch (error) {
      const fieldErrors = extractFieldErrors(error?.data, TRANSACTION_FIELDS);
      if (Object.keys(fieldErrors).length > 0) {
        setErrors((current) => ({ ...current, ...fieldErrors }));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModalShell
      title="New transaction"
      description="Log income, an expense, or move funds between envelopes."
      onClose={onClose}
    >
      <form className="modal-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label className="field">
            <span>Type</span>
            <select name="kind" value={form.kind} onChange={updateField}>
              {transactionKinds.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Amount</span>
            <input
              type="number"
              min="0.01"
              step="0.01"
              name="amount"
              value={form.amount}
              onChange={updateField}
              placeholder="0.00"
            />
            {errors.amount ? <small>{errors.amount}</small> : null}
          </label>

          {form.kind !== "deposit" ? (
            <label className="field">
              <span>Source category</span>
              <select name="source_category" value={form.source_category} onChange={updateField}>
                <option value="">Select a category</option>
                {sortedCategories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              {errors.source_category ? <small>{errors.source_category}</small> : null}
            </label>
          ) : null}

          {form.kind !== "withdraw" ? (
            <label className="field">
              <span>Destination category</span>
              <select
                name="destination_category"
                value={form.destination_category}
                onChange={updateField}
              >
                <option value="">Select a category</option>
                {sortedCategories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              {errors.destination_category ? <small>{errors.destination_category}</small> : null}
            </label>
          ) : null}

          <label className="field">
            <span>Time</span>
            <input
              type="datetime-local"
              name="occurred_at"
              value={form.occurred_at}
              onChange={updateField}
            />
          </label>

          <label className="field field--full">
            <span>Description</span>
            <textarea
              rows="3"
              name="description"
              value={form.description}
              onChange={updateField}
              placeholder="What was this for? e.g. weekly groceries"
            />
          </label>
        </div>

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Processing..." : "Save transaction"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}
