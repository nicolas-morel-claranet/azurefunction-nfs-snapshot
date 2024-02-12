from datetime import datetime, timedelta
from collections import defaultdict
from azure.storage.fileshare import (
    ShareServiceClient,
    generate_account_sas,
    ResourceTypes,
    AccountSasPermissions,
)
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.subscription import SubscriptionClient


class AzureNfsSnapshot(object):
    def __init__(self):
        self.azconn = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
        self.subscriptions_list = self.subscriptions_list()
        self.filestorage_list = self.get_all_filestorage(
            subscriptions_list=self.subscriptions_list
        )
        self.sas_token = {}

    def subscriptions_list(self):
        sublist = []
        for sub in SubscriptionClient(credential=self.azconn).subscriptions.list():
            sublist.append(sub.subscription_id)
        return sublist

    def get_all_filestorage(self, subscriptions_list):
        filestorage_hash = defaultdict(dict)
        for sub in subscriptions_list:
            resourceconn = ResourceManagementClient(
                credential=self.azconn, subscription_id=sub
            )
            rg_list = resourceconn.resource_groups.list()
            for rg in rg_list:
                for sa in resourceconn.resources.list_by_resource_group(
                    resource_group_name=rg.name,
                    filter="resourceType eq 'Microsoft.Storage/storageAccounts'",
                ):
                    if sa.kind == "FileStorage" and sa.sku.tier == "Premium":
                        setattr(sa, "resourcegroup", rg.name)
                        setattr(sa, "subscription_id", sub)
                        filestorage_hash[sa.name] = sa
        return filestorage_hash

    def _generate_sas_token(self, storage_account):
        # Get access key
        sa_client = StorageManagementClient(
            credential=self.azconn,
            subscription_id=self.filestorage_list[storage_account].subscription_id,
        )
        key = (
            sa_client.storage_accounts.list_keys(
                resource_group_name=self.filestorage_list[
                    storage_account
                ].resourcegroup,
                account_name=storage_account,
            )
            .keys[0]
            .value
        )
        return generate_account_sas(
            account_name=storage_account,
            account_key=key,
            resource_types=ResourceTypes(service=True, object=True, container=True),
            permission=AccountSasPermissions(
                read=True, write=True, delete=True, list=True, create=True
            ),
            expiry=datetime.utcnow() + timedelta(minutes=10),
        )

    def _get_sas_token(self, storage_account):
        if storage_account not in self.sas_token.keys():
            self.sas_token[storage_account] = self._generate_sas_token(
                storage_account=storage_account
            )
        return self.sas_token[storage_account]

    def list_snapshot(self, storage_account, share_name=None):
        sas_token = self._get_sas_token(storage_account=storage_account)
        file_service = ShareServiceClient(
            account_url=f"https://{storage_account}.file.core.windows.net/",
            credential=sas_token,
        )
        if share_name:
            return [
                share
                for share in file_service.list_shares(include_snapshots=True)
                if share.snapshot and share.name == share_name
            ]
        else:
            return [
                share
                for share in file_service.list_shares(include_snapshots=True)
                if share.snapshot
            ]

    def get_last_snapshot(self, storage_account, share_name):
        snapshot_list = [
            share.snapshot
            for share in self.list_snapshot(storage_account=storage_account)
            if share.name == share_name
        ]
        snapshot_list.sort(reverse=True)
        try:
            return snapshot_list[0]
        except IndexError:
            return False

    def list_shares(self, storage_account):
        sas_token = self._get_sas_token(storage_account=storage_account)
        print(f"{storage_account} sas_token : {sas_token}")
        file_service = ShareServiceClient(
            account_url=f"https://{storage_account}.file.core.windows.net/",
            credential=sas_token,
        )
        return [share for share in file_service.list_shares()]

    def create_snapshot(self, storage_account, share):
        sas_token = self._get_sas_token(storage_account=storage_account)
        print(f"{storage_account} sas_token : {sas_token}")
        file_service = ShareServiceClient(
            account_url=f"https://{storage_account}.file.core.windows.net/",
            credential=sas_token,
        )
        share = file_service.get_share_client(share)
        return share.create_snapshot()

    def delete_snapshot(self, storage_account, share, snapshot):
        sas_token = self._get_sas_token(storage_account=storage_account)
        print(f"{storage_account} sas_token : {sas_token}")
        file_service = ShareServiceClient(
            account_url=f"https://{storage_account}.file.core.windows.net/",
            credential=sas_token,
        )
        share = file_service.get_share_client(share, snapshot=snapshot)
        if share.snapshot:
            return share.delete_share()
        else:
            return f"{storage_account} - {share} - {snapshot} - Not a snapshot"
