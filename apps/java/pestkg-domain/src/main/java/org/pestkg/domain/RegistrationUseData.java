package org.pestkg.domain;

import java.util.List;

public record RegistrationUseData(
        String useId,
        String jurisdiction,
        String productId,
        String productLabelOriginal,
        String productLabelEn,
        List<EntityRef> activeIngredients,
        List<EntityRef> crops,
        List<EntityRef> targets,
        List<EntityRef> formulations,
        String registrationStatus,
        String registrationDate,
        String expiryDate,
        String pairingStatus,
        String sourceRecordId,
        String sourceUrl) {
}
