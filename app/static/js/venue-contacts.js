/**
 * Venue Contacts - Dynamic Form Management
 * Permet d'ajouter/supprimer des contacts dans le formulaire venue
 */
document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('contacts-container');
    const addBtn = document.getElementById('add-contact-btn');

    if (!container || !addBtn) return;

    // Compteur pour les index uniques des contacts
    let contactIndex = document.querySelectorAll('.contact-row').length;

    // Template HTML pour un nouveau contact
    function getContactTemplate(index) {
        return `
            <div class="contact-row border rounded p-3 mb-3">
                <div class="row g-3">
                    <div class="col-md-3">
                        <input type="text" class="form-control" name="contacts[${index}][name]"
                               placeholder="Nom *" required>
                    </div>
                    <div class="col-md-2">
                        <select class="form-select" name="contacts[${index}][role]">
                            <option value="">Rôle</option>
                            <option value="Booker">Booker</option>
                            <option value="Production">Production</option>
                            <option value="Sound Engineer">Ingénieur son</option>
                            <option value="Lighting">Éclairagiste</option>
                            <option value="Stage Manager">Régisseur</option>
                            <option value="Security">Sécurité</option>
                            <option value="Marketing">Marketing</option>
                            <option value="Box Office">Billetterie</option>
                            <option value="Hospitality">Hospitalité</option>
                            <option value="General Manager">Directeur</option>
                            <option value="Other">Autre</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <input type="email" class="form-control" name="contacts[${index}][email]"
                               placeholder="Email">
                    </div>
                    <div class="col-md-3">
                        <input type="tel" class="form-control" name="contacts[${index}][phone]"
                               placeholder="Téléphone">
                    </div>
                    <div class="col-md-1 d-flex align-items-center">
                        <button type="button" class="btn btn-outline-danger btn-sm remove-contact" title="Supprimer">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // Ajouter nouveau contact
    addBtn.addEventListener('click', function() {
        container.insertAdjacentHTML('beforeend', getContactTemplate(contactIndex));
        contactIndex++;
    });

    // Supprimer contact (event delegation)
    container.addEventListener('click', function(e) {
        const removeBtn = e.target.closest('.remove-contact');
        if (removeBtn) {
            const row = removeBtn.closest('.contact-row');
            if (row) {
                // Animation de suppression
                row.style.transition = 'opacity 0.2s, transform 0.2s';
                row.style.opacity = '0';
                row.style.transform = 'translateX(-10px)';
                setTimeout(() => row.remove(), 200);
            }
        }
    });
});
