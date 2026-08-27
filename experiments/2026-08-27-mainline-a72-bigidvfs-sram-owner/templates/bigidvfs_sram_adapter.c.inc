int
mt6797_bigidvfs_sram_enable(struct device *dev,
			    const struct mt6797_bigidvfs_sram_request *request,
			    struct mt6797_bigidvfs_sram_result *result)
{
	struct mt6797_bigidvfs_backend *backend;
	int ret;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_bigidvfs_sram_result){};
	if (!dev)
		return -EINVAL;
	backend = dev_get_drvdata(dev);
	if (!backend)
		return -ENODEV;

	mutex_lock(&backend->operation_lock);
	if (backend->faulted) {
		ret = -EIO;
		goto out_unlock;
	}
	ret = mt6797_bigidvfs_sram_owner_execute(&backend->sram_owner,
						 &mt6797_bigidvfs_sram_ops,
						 backend, request, result);
	if (ret && result->error)
		mt6797_bigidvfs_mark_fault(backend);

out_unlock:
	mutex_unlock(&backend->operation_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_bigidvfs_sram_enable);
