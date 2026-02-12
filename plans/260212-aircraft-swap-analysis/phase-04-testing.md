# Phase 04: Testing & Verification
Status: ✅ Complete
Dependencies: Phase 01, 02, 03

## Objective
Verify toàn bộ feature Aircraft Swap Analysis hoạt động end-to-end.

## Automated Tests
- [ ] 1. Unit test `swap_detector.py` - detection logic
- [ ] 2. Unit test swap reason classification
- [ ] 3. API test `/api/swap/summary` response format
- [ ] 4. API test `/api/swap/events` pagination
- [ ] 5. API test `/api/swap/reasons` aggregation
- [ ] 6. Run existing test suite: `pytest tests/ -v`

## Integration Tests
- [ ] 7. End-to-end: AIMS sync → swap detection → API → Dashboard
- [ ] 8. Verify X-API-Key protection on all swap endpoints

## Browser Tests
- [ ] 9. Load `/aircraft-swap` page in browser
- [ ] 10. Verify KPI cards populate
- [ ] 11. Verify period toggle works
- [ ] 12. Verify swap log pagination
- [ ] 13. Verify export CSV download

## Test Commands
```bash
# Run all existing tests + new swap tests
pytest tests/ -v

# Run only swap tests
pytest tests/test_swap.py -v

# Run API server for browser test
python run_server.py
# Then open http://localhost:5000/aircraft-swap
```

## Files to Create
- `tests/test_swap.py` - [NEW] Swap feature test suite

---
End of Phases
