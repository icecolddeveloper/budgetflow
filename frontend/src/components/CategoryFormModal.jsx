import { useState } from "react";

import { ModalShell } from "./ModalShell";

const iconOptions = [
  { value: "wallet", label: "Wallet" },
  { value: "utensils-crossed", label: "Food" },
  { value: "car-front", label: "Transport" },
  { value: "building-2", label: "Housing" },
  { value: "piggy-bank", label: "Savings" },
  { value: "party-popper", label: "Entertainment" },
  { value: "circle-dollar-sign", label: "Income" },
];

export function CategoryFormModal({ category, onClose, onSubmit }) {
  const [form, setForm] = useState({
    name: category?.name || "",
    description: category?.description || "",
    icon: category?.icon || "wallet",
    color: category?.color || "#0f766e",
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const nextErrors = {};
    if (!form.name.trim()) {
      nextErrors.name = "Category name is required.";
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit({
        ...form,
        name: form.name.trim(),
        description: form.description.trim(),
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModalShell
      title={category ? "Edit category" : "Add category"}
      description="Each category is an envelope your money lives in."
      onClose={onClose}
    >
      <form className="modal-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label className="field">
            <span>Name</span>
            <input
              name="name"
              value={form.name}
              onChange={updateField}
              placeholder="Savings, groceries, rent..."
            />
            {errors.name ? <small>{errors.name}</small> : null}
          </label>

          <label className="field">
            <span>Icon</span>
            <select name="icon" value={form.icon} onChange={updateField}>
              {iconOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field field--full">
            <span>Description</span>
            <textarea
              name="description"
              rows="3"
              value={form.description}
              onChange={updateField}
              placeholder="What goes in this envelope? Add a note."
            />
          </label>

          <label className="field field--full">
            <span>Accent color</span>
            <div className="color-field">
              <input type="color" name="color" value={form.color} onChange={updateField} />
              <input name="color" value={form.color} onChange={updateField} />
            </div>
          </label>
        </div>

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Saving..." : category ? "Save changes" : "Create category"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}
