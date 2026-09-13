'use strict';

const { Contract } = require('fabric-contract-api');

/**
 * Tamper-evident audit records for the SIH26188 screening system.
 * The ledger holds ONLY: verificationId, recordHash (SHA-256), officerId, timestamp.
 * No images, no biometric data, no PII.
 */
class VerificationContract extends Contract {

    _key(ctx, verificationId) {
        return ctx.stub.createCompositeKey('verification', [verificationId]);
    }

    /**
     * registerVerification(verificationId, recordHash, officerId?)
     * Append-only: rejects an attempt to overwrite an existing record.
     */
    async registerVerification(ctx, verificationId, recordHash, officerId = '') {
        if (!verificationId || !recordHash) {
            throw new Error('verificationId and recordHash are required');
        }
        const key = this._key(ctx, verificationId);
        const existing = await ctx.stub.getState(key);
        if (existing && existing.length > 0) {
            throw new Error(`Verification ${verificationId} already registered`);
        }
        const record = {
            docType: 'VerificationAudit',
            verificationId,
            recordHash,
            officerId,
            txId: ctx.stub.getTxID(),
            timestamp: ctx.stub.getDateTimestamp().toISOString(),
        };
        await ctx.stub.putState(key, Buffer.from(JSON.stringify(record)));
        ctx.stub.setEvent('VerificationRegistered', Buffer.from(JSON.stringify(record)));
        return JSON.stringify(record);
    }

    /** getVerification(verificationId) -> record JSON */
    async getVerification(ctx, verificationId) {
        const data = await ctx.stub.getState(this._key(ctx, verificationId));
        if (!data || data.length === 0) {
            throw new Error(`Verification ${verificationId} not found`);
        }
        return data.toString();
    }

    /** verifyIntegrity(verificationId, currentHash) -> "INTACT" | "TAMPERED" */
    async verifyIntegrity(ctx, verificationId, currentHash) {
        const data = await ctx.stub.getState(this._key(ctx, verificationId));
        if (!data || data.length === 0) {
            throw new Error(`Verification ${verificationId} not found`);
        }
        const record = JSON.parse(data.toString());
        return record.recordHash === currentHash ? 'INTACT' : 'TAMPERED';
    }

    /** getHistory(verificationId) -> array of {txId, timestamp, value, isDelete} */
    async getHistory(ctx, verificationId) {
        const iterator = await ctx.stub.getHistoryForKey(this._key(ctx, verificationId));
        const results = [];
        for (let res = await iterator.next(); !res.done; res = await iterator.next()) {
            const item = res.value;
            results.push({
                txId: item.txId,
                timestamp: item.timestamp,
                isDelete: item.isDelete,
                value: item.value && item.value.length ? JSON.parse(item.value.toString()) : null,
            });
        }
        await iterator.close();
        return JSON.stringify(results);
    }
}

module.exports = { VerificationContract };
